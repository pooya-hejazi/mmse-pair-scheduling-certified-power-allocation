# Novelty and publication obstacle resolution — 31 October 2026

**نتیجه:** سه مانع فنی مشخص برطرف شد: اثبات با بعد گیرندهٔ ثابت، حل سراسری زیرمسئلهٔ توان یک زوج، و تولید گواه معتبر برای یک نمونهٔ شبکه. نوآوری نسبت به تمام پیشینه و کفایت برای انتشار هنوز اثبات نشده است. مسیر پیشنهادی اکنون «مرز پیچیدگی و گواه بهینگی برای زمان‌بندی زوج‌ها با توان پیوسته و گیرندهٔ MMSE» است؛ نتیجهٔ منفی تخصیص انتخابی CSI محفوظ می‌ماند.

| مانع | وضعیت و شاهد | محدودیت باقی‌مانده |
|---|---|---|
| رشد تعداد آنتن در اثبات سختی قبلی | FIXED_DIMENSION.md: کاهش با M=3، کانال‌های گویا و هم‌نُرم؛ بازبینی مستقل ریاضی PASS مشروط به قضیهٔ مرجع | مدل ساختگیِ آزاد بین منابع؛ تحقق در مدل مشترک پرتوها اثبات نشده؛ نوآوری این محدودسازی باز است |
| بهینه‌سازی غیرمقعر توان یک زوج | CONTINUOUS_EXACT.md: آستانهٔ دقیق تقعر و حداکثر 17 نامزد روی مستطیل؛ اثبات مستقل کنترل شد | وزن‌های نابرابر و قیود محلیِ غیرمستطیلی پوشش داده نشده‌اند |
| اعتماد به ریشه‌های عددی و دوگان تقریبی | rational_oracle.py: جداسازی ریشهٔ گویا، کران جهت‌دار لگاریتم و شکست صریح در عدم‌قطعیت؛ بازبینی نرم‌افزار PASS | وابستگی به صحت قرارداد SymPy و Decimal؛ تضمین زمان اجرا برای هر ورودی نداریم |
| اتصال گواه زوج به شبکه | NETWORK-CR015-A01: بازبینی تمام 112 قیمت‌گذاری و محاسبات اولیه/دوگان PASS | فقط یک ورودی توسعهٔ 8کاربره؛ گواه برای کانال ذخیره‌شده و CSI کامل |
| هم‌پوشانی با پیشینه | PRIORITY_SCREEN.md: مقایسهٔ محدود و صریح با منابع نزدیک | متن کامل Mostafa2022 هنوز دریافت نشده؛ جست‌وجو کافی برای ادعای اولویت نیست |
| ارزش عملکردی و مقایسهٔ هم‌بودجه | SYSTEM_MODEL.md و NEXT_EVALUATION.md: مدل، معیارها و قرارداد مقایسه مشخص شد | برتری نسبت به I-WMMSE، روش‌های جدید و GPU هنوز تأیید نشده |
| کفایت مقاله | ادعاها محدود و نتایج منفی حفظ شدند | مراحل علمی S03/S03G پذیرفته نیستند؛ ارزیابی تأییدی و مقالهٔ نهایی شروع نشده‌اند |

## Certified development result

For the existing K=8, M=32, S=4 input and total radiated power 0.8 W, the selected grid schedule is feasible for the continuous-power joint problem. Independent review established the outward-rounded enclosure

    86.85363628 <= continuous integral optimum / ln(2)
                  <= continuous configuration LP optimum / ln(2)
                  <= 87.54028709.

The incumbent attains at least the lower endpoint. Its certified relative shortfall is below **0.790584%**. These are summed spectral-efficiency terms, not measured bit/s throughput or improvement over another method. The grid LP and grid MILP numerical objectives agreed to solver precision on this instance; this is not a general integrality proof. The upper bound explicitly covers all continuous powers in [.05,.2] W, using exact all-pair dual repair. Original run: 7.789 seconds externally, 4.945 seconds internally, against a 45-second cap; no GPU acceleration. Independent certificate check: 5.578 seconds under 30 seconds.

The new bound and the earlier approximately 9% grid allowance are different constructions. Their numbers must not be reported as a throughput improvement or a population-level speed/accuracy comparison.

## Evidence and audits

- RESOLUTION-CR015-A01: technical proof PASS conditional on the cited bounded perfect-3DM theorem; independent symbolic checks and all 556 rational forest templates passed. Scientific novelty/integration unverified.
- ORACLE-CR015-A01: isolated software PASS; independent exact-optimum, repeated-root, signed-price, degenerate-box and failure checks passed.
- NETWORK-CR015-A01: scoped network certificate PASS, including independent recalculation of all 112 pair prices, exact schedule/power and dual arithmetic. Scientific-stage acceptance unverified.

All three are initial supporting technical reviews, each 1/2 attempts used under its distinct contract. They do not consume or accept CP-S03/S03G. Full audit records remain under audit/reviews/<attempt>; research-branch exports under review/<attempt> are byte-identical copies, not new reviews. Frozen input manifests identify the exact reviewed versions. The authored theorem files retain their original pre-review wording; the audit reports supply the later verdicts without altering frozen source. Exported reviewer scripts retain their original local snapshot paths for provenance and are not standalone rerun commands in the export directory.

## Reproduction and scope

The numerical and exact checks use the existing NumPy/SciPy environment; the certified implementation additionally uses SymPy 1.14 and Python Decimal. Scripts preserve archived manifests/results by refusing selected overwrites. Do not rerun in place to replace the evidence. Use a separate disposable copy and retain source/input hashes. The K8 integration also requires the local pinned research/comparison/inputs/power-8.npz; this raw channel file is not included in this upload. Thus the repository contains source and certificates, not a claim that the entire upstream dataset is redistributable or independently reconstructed here.

No original research script, S02 evidence, or old frozen theorem was changed. No estimator was retrained. No general polynomial-time ILP solver, general LP exactness, publication priority, journal acceptance, or comprehensive 6G architecture is claimed.

## Remaining full text and next decision

The concrete missing close source is [Mostafa, Sung and Guo (2022)](https://doi.org/10.1109/ACCESS.2022.3152531), *Joint Computation and Communication Resource Allocation with NOMA and OMA Offloading for Multi-server Systems in F-RAN*. The [institutional record](https://scholars.cityu.edu.hk/en/publications/joint-computation-and-communication-resource-allocation-with-noma/) lists a published PDF, but direct retrieval returned HTTP403. Indexed passages are only a lead. The four supplied Ruder/Fan files are available and need not be requested again.

The source premise for bounded perfect-3DM is explicitly stated on p.141, §2, eq.(2.1) of the [Dyer--Frieze author paper](https://www.math.cmu.edu/~af1p/Texfiles/COMPLEXPART.pdf). The coordinator rechecked that statement and saved a hashed local PDF after the mathematical audit; this is additional provenance, not a retroactive independent re-review or a reproduction of the cited 1986 proof.

Proceed with the precise full-text priority comparison and the frozen model/evaluation proposal. If those support a substantive contribution, use the accepted planning process for matched comparisons before the requested formal >=30-paper related-work table and final article prose. Correct lemmas and one small gap are promising evidence, not publication sufficiency.
