from pathlib import Path
p=Path('build_cdl.py'); s=p.read_text(encoding='utf-8')
s=s.replace('corr = [float(row["r"]) for row in pairs]', 'corr = [float(F(row["r"])) for row in pairs]')
p.write_text(s,encoding='utf-8'); print('ok')
