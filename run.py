import main as m

exec(compile(open("patch.py", encoding="utf-8").read(), "patch.py", "exec"), m.__dict__)
m.main()
