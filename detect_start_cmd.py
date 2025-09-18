#!/usr/bin/env python3
"""
detect_start_cmd.py <repo_path>
- 저장소를 파이썬 AST로 분석해서 실제 코드 상의 진입점 호출만 탐지합니다.
- FastAPI:   var = FastAPI(...)  → uvicorn {module}:{var} --port $PORT
- Flask:     var = Flask(...)    → gunicorn {module}:{var} -b 0.0.0.0:$PORT
- 문자열/주석 속 'FastAPI(...)' / 'Flask(...)' 는 무시합니다.
"""
import os, sys, ast

def rel_module(repo, file_path):
    rel = os.path.relpath(file_path, repo)
    if rel.endswith(".py"):
        rel = rel[:-3]
    # __init__.py 는 모듈명에서 제외
    if rel.endswith("__init__"):
        rel = rel[:-9]
    return rel.replace("/", ".").replace("\\", ".")

def get_callee_name(call: ast.Call):
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None

def scan_file(repo, path):
    # detect 스크립트 자신은 제외
    if os.path.basename(path) == "detect_start_cmd.py":
        return []
    try:
        src = open(path, "r", encoding="utf-8", errors="ignore").read()
        tree = ast.parse(src, filename=path)
    except Exception:
        return []

    found = []  # (framework, module, varname, file_path)
    for node in ast.walk(tree):
        # var = FastAPI(...), var = Flask(...)
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            callee = get_callee_name(node.value)
            if callee not in {"FastAPI", "Flask"}:
                continue
            # 좌변 변수명만 취함 (x, y = ... 같은 패턴 제외)
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                continue
            varname = node.targets[0].id
            module = rel_module(repo, path)
            framework = "FastAPI" if callee == "FastAPI" else "Flask"
            found.append((framework, module, varname, path))
    return found

def scan_repo(repo):
    hits = []
    for root, _, files in os.walk(repo):
        for f in files:
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            hits.extend(scan_file(repo, p))
    # 우선순위: FastAPI → Flask
    fast = [h for h in hits if h[0] == "FastAPI"]
    flsk = [h for h in hits if h[0] == "Flask"]
    if fast:
        return fast[0]
    if flsk:
        return flsk[0]
    return None

def main():
    if len(sys.argv) < 2:
        print("usage: detect_start_cmd.py <repo_path>", file=sys.stderr)
        sys.exit(1)
    repo = os.path.abspath(sys.argv[1])
    if not os.path.isdir(repo):
        print(f"not a directory: {repo}", file=sys.stderr); sys.exit(2)

    hit = scan_repo(repo)
    if hit:
        framework, module, varname, path = hit
        print(f"# detected({framework}): {os.path.relpath(path, repo)}  ->  {module}:{varname}")
        if framework == "FastAPI":
            print(f'LEGACY_CMD="DATA_DIR=\\$DATA_DIR uvicorn {module}:{varname} --host 0.0.0.0 --port \\$PORT"')
        else:
            print(f'LEGACY_CMD="DATA_DIR=\\$DATA_DIR gunicorn -w 1 -b 0.0.0.0:\\$PORT {module}:{varname}"')
        return

    # 미발견 시 예시 2개 출력
    print('# fallback example (uvicorn): main.py 안에 app=FastAPI(...)가 있다고 가정')
    print('LEGACY_CMD="DATA_DIR=\\$DATA_DIR uvicorn main:app --host 0.0.0.0 --port \\$PORT"')
    print('# fallback example (gunicorn): app.py 안에 app=Flask(...)가 있다고 가정')
    print('LEGACY_CMD="DATA_DIR=\\$DATA_DIR gunicorn -w 1 -b 0.0.0.0:\\$PORT app:app"')

if __name__ == "__main__":
    main()

