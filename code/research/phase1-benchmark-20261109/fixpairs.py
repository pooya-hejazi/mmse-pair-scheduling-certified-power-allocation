from pathlib import Path
p=Path('run_pilot.py'); s=p.read_text(encoding='utf-8')
s=s.replace('return [(u, v, str(powers[u]), str(powers[v])) for u, v in pairs]',
            'return [(min(u, v), max(u, v), str(powers[u]), str(powers[v])) for u, v in pairs]')
s=s.replace('pairs = [(int(perm[2 * t]), int(perm[2 * t + 1])) for t in range(s)]',
            'pairs = [tuple(sorted((int(perm[2 * t]), int(perm[2 * t + 1])))) for t in range(s)]')
p.write_text(s, encoding='utf-8'); print('ok')
