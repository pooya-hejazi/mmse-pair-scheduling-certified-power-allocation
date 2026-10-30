# Matching با قیمت منبع: LP دقیق کجا و کران کجا؟

U=2Sکاربر، Sمنبع، هرگروه دقیقاًدوکاربر، هرکاربر یک‌بار خدمت، تمام pairها مجاز. امتیاز ثابت q_es برای edge/pair e وresource s ازمدلفیزیکی مشخص به‌دست می‌آید. این نظریه فعلاًfixedpower وCSIورودیثابت است؛ بودجه توان/عدم‌قطعیت می‌تواند ساختار را عوض کند.

مدلIP: max Σ_es q_es x_es باdegreeهرکاربر۱، هرresourceدقیقاً۱گروه، x∈{0,1}. LPعادی x≥0اینقیود را حفظ می‌کند. برای هرsubset فرد O، قید Σ_(e⊂O),s x_es≤(|O|−1)/2را اضافه کنید و LPحاصل راP_oddبنامید.

Projection y_e=Σ_s x_es درpolytopeperfectmatchingقرارمی‌گیرد. قضیهEdmonds یک نتیجه کلاسیک است؛ مرجع آموزشی اولیه [Norin،Theorem5](https://www.math.mcgill.ca/snorin/papers/lecture2.pdf)، و شرح حل باseparation oracle در[CMU2018](https://cmualgos.github.io/2018/09/12/matchings-via-LPs.html). تعدادodd-setها نمایی است، هرچندmatching وseparationچندجمله‌ای هستند. درکدکوچک اینقیود وmatchingها صریحاًشمرده شده‌اند؛ این implementationمقیاس‌پذیریچندجمله‌ای را نشان نمی‌دهد.

اگر q_es=w_e+b_s باشد،maximizationبهperfectmatchingباوزنw وΣbتقلیل می‌یابد. گروه‌ها به هرresourceبایکتا تخصیص می‌یابند وP_oddدارای optimumصحیح است. این زیرکلاس generalgraphmatching است، نه صرفاًbipartiteassignment، و نتیجه جدیدبنیادی نیست.

برای هرقیمتآزادλ_s تعریف کنید:

    U(λ)=Σ_s λ_s + max_(M perfect matching) Σ_(e∈M) max_s(q_es−λ_s).

هرجوابصحیح به‌اندازهU(λ)یاکمترهدفدارد:قیمت منابع یک‌بارجمع می‌شود و هرedgeازبهترینresourceممکن سود می‌گیرد. این upper bound نسبتبه خانوادهکاملتعریفشده است. کمینه‌کردنU(λ) معادلvalueِP_oddاست، به‌واسطهdualizationقیدهایresourceوpolytopematching. این ساختارLagrangianکلاسیک است؛ [Balas–Saltzman۱۹۹۱](https://doi.org/10.1287/opre.39.1.150) نیز برایassignmentسه‌شاخصی ازrelaxationلاگرانژ وfacetها استفاده می‌کند؛ صرفنامpricingنوآوری نیست.

**شرط کافی exactness:** اگرmatching M*بخشmaxراحل کند وبتوان edgeهایآنرا بهresourceهایdistinctازمجموعهargmax_s(q_es−λ_s)تخصیصداد، جوابصحیحی باهدفU(λ)به‌دست می‌آید. پسIP وP_oddهر دوtightاند. tiesباید باmatchingدوبخشیedge–resourceحل شوند، نهargmaxدلخواه. عدمیافتناینcertificateبراییکM*انتخاب‌شده اثباتعدموجودcertificateبرایهمهmatchingهایبهینه نیست.

درغیراینصورت، assignmentبهینهresourceبرایmatchingحاصل یکlowerboundشدنیLمی‌دهد وU−Lگواهresidualاست. Lمی‌تواندازoptفاصلهداشتهباشد حتی وقتیLPtightاست؛ gapحل‌گر و ضعفprimalrecoveryجدا گزارش شوند. λازdualِLPoddدرbenchmarkگرفته شد وUآن مستقلاًازmatchingمحاسبه شد؛ این کار چرخهحلjointمستقلجدید یاLPfreealgorithmنیست.

کدsolver_study.pyبرای۴/۶/۸UEاست. چونenvironmentعلمی اولیهnetworkxنداشت، oracleصریح۱۰۵matchingحداکثر استفادهشد؛چیزینصبنشد. MILPمرجعHiGHS،LPodd/fullوweakرویهمانqهستند. checks.pyهمه۲۴۰optimumصحیح راازenumerationmatching+assignmentبازحسابمی‌کند. ادعایسرعتبزرگ یاGPUبرایاینbenchmarkوجودندارد.

**رابط آینده بااطلاعاتکانال:** باfamilyثابتوخطایهمزمان|q−qhat|≤ε، گواه regret ≤ U(qhat+ε)−(qhat−ε)ᵀdبرایincumbentشدنی d معتبر است. این کران ازsolvergapوCSIuncertaintyتأثیرمی‌گیرد؛ تعقیبsolver تاgapصفر همیشهبهترکردننرخواقعی نیست. ساختεباپوشش معتبر ودوطرفه وکنترلاثرselectionهنوزtaskبازاست. قاعده«اطلاعات بیشتر یا محاسبه بیشتر» نامزدسهمپژوهشی است، نه نتیجه اثبات‌شدهآزمایش‌ها.
