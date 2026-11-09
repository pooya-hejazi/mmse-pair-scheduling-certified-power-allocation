from pathlib import Path
p=Path('PHASE1_REPORT.md'); s=p.read_text(encoding='utf-8')
s=s.replace('Absolute gains: K=16 ray cases gain about 0.9 nat (1.3 bit/s/Hz) at the median; controlled cases about 0.2 nat (0.3 bit/s/Hz). Both exceed the 0.05 bit/s/Hz material threshold; the 2% relative threshold is not met by the pooled median.',
'''Absolute gains must be converted with the paper's gross occupied-tone SE convention, `SE = Q/(S ln 2)`, where `S=8` here. K=16 ray cases gain about 0.9 nat total at the median, i.e. about **0.16 bit/s/Hz**; controlled cases gain about 0.2 nat, i.e. about **0.034 bit/s/Hz**, which is below the 0.05 bit/s/Hz threshold. The pooled median is about 0.38 nat, i.e. about **0.069 bit/s/Hz**. The headline absolute claim therefore rests on the ray-traced K=16 pool; the controlled pool is corroborating but does not independently clear 0.05 bit/s/Hz. The 2% relative threshold is not met by the pooled median.''')
p.write_text(s,encoding='utf-8'); print('ok')
