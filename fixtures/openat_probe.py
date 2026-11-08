#!/usr/bin/env python3
"""openat_probe.py: measure claim.py --root on the rows in fixtures/openat-walk-spec.md (exori, 2026-11-08).
Prints the current verdict per row. A probe, not a pass/fail fixture yet: rows 2, 5, 6, 7 differ from the spec until the walk lands."""
import hashlib, os, tempfile, importlib.util
spec = importlib.util.spec_from_file_location("claim", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples", "claim.py"))
claim = importlib.util.module_from_spec(spec); spec.loader.exec_module(claim)
H=lambda b: hashlib.sha256(b).hexdigest()
def run(cid, setup, name, content, hook_fn=None, hook_name=None):
    with tempfile.TemporaryDirectory() as d:
        root=os.path.join(d,"root"); os.mkdir(root); out=os.path.join(d,"out"); os.mkdir(out)
        setup(root,out)
        raw=f"verified.\nread: {name} sha256:{H(content)}\n"
        real=getattr(os,hook_name) if hook_name else None
        fired=[False]
        if hook_name:
            def hooked(p,*a,**k):
                if not fired[0] and str(p).endswith(name.split('/')[-1]):
                    fired[0]=True; hook_fn(root,out)
                return real(p,*a,**k)
            setattr(os,hook_name,hooked)
        try: msg=claim.root_mismatch(raw,root)
        finally:
            if hook_name: setattr(os,hook_name,real)
        print(f"{cid:28} {'accept' if msg is None else 'refuse'}  {msg or ''}")
def w(p,b): open(p,"wb").write(b)
def base(root,out):
    os.mkdir(f"{root}/sub"); w(f"{root}/sub/report.txt",b"inside\n")
    os.mkdir(f"{out}/sub"); w(f"{out}/sub/report.txt",b"outside\n"); w(f"{out}/report.txt",b"outside\n")
def swapdir(root,out):
    os.rename(f"{root}/sub",f"{root}/sub.old"); os.symlink(f"{out}/sub",f"{root}/sub")
run("control-nested",base,"sub/report.txt",b"inside\n")
run("dir-swap-before-lstat",base,"sub/report.txt",b"outside\n",swapdir,"lstat")
run("dir-swap-before-open",base,"sub/report.txt",b"outside\n",swapdir,"open")
def symin(root,out):
    os.mkdir(f"{root}/real"); w(f"{root}/real/report.txt",b"inside\n"); os.symlink("real",f"{root}/sub")
run("static-dir-symlink-inside",symin,"sub/report.txt",b"inside\n")
def symout(root,out):
    w(f"{out}/report.txt",b"outside\n"); os.symlink(out,f"{root}/sub")
run("static-dir-symlink-outside",symout,"sub/report.txt",b"outside\n")
def leafsym(root,out):
    w(f"{root}/real.txt",b"inside\n"); os.symlink("real.txt",f"{root}/report.txt")
run("static-leaf-symlink-inside",leafsym,"report.txt",b"inside\n")
def dotdot(root,out):
    os.mkdir(f"{root}/sub"); w(f"{root}/report.txt",b"inside\n")
run("dotdot-stays-inside",dotdot,"sub/../report.txt",b"inside\n")
