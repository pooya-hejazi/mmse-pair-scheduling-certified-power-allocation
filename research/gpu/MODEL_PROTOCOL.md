# CR007 — مدل مشترک توان، اطلاعات و تخصیص با ارزیابی GPU

این سند packet قبل اجراست. هدف، مدل قابل دفاع برای uplink user-centric/cell-free در مسیر6G است؛ پوشش همه قابلیت‌های6G ادعا نمی‌شود. APها در نسخه اول ثابت و همفاز، کاربران single-antenna، منابع orthogonal، گروه‌ها حداکثر۲UE، receiver linear-MMSE و estimator ثابت‌اند. RIS،ISAC،THzhardware،HARQ،mobility/doppler،multi-CPUbackhaul وکنترلتوانپیوسته در این benchmark مدل نشده‌اند. این مرزها باید در مقاله دیده شوند.

## صورت دقیق مدل

ستون c=(g,s,p_g,a_g) یک گروه مجاز، RB، بردار توان از grid ازپیش‌مشخص و پروفایل AP مجاز را تعریف می‌کند. درMVP پروفایلAP فقطهمه۴APثابت است. با ورودی CSI ثابت، نرخ هرUE درهرستون ازSINR واقعی مدل receiver محاسبه می‌شود. z_c دودویی است؛ نرخ کل،توان،energyوfronthaul هرستون ضرایب ثابت‌اند. قیود:

- هرUE دقیقاًیک‌بار خدمت یاadmissionمتغیرصریح؛ درbenchmarkاول exact-cover وبدونdrop.
- هرRB حداکثریک گروه؛درU=2SهمهRBهاپر وگروه‌هادونفره‌اند.
- P_u≤P_u,max ازطریقgrid/eligibility؛ Σ_c P_c z_c≤P_budget.
- درنسخه دارایQoS،Σ_c R_uc z_c≥R_u,min؛ناممکنبودنثبت،نهحذفنمونه.
- اگرAPprofileمتغیرشود،Σ_c F_ac z_c≤C_a برایfronthaul وپردازشAP. هزینهساختتمامprofileها بایدشمردهشود.
- هزینهpilot،controlوcompute اززمانpayloadکسرشود؛ τ+ℓ<T. نرخbit/s = B_s log₂(1+SINR)×prelog. نرخSEوthroughputجداگزارش‌شوند.

دو مسئله مکمل: (P-T) بیشینهthroughputبرایبودجهتوانمعلوم؛(P-E) کمینهتوانبرایحدthroughputمعلوم. efficiency=bit/Jازتوانمخابره+مدلثابتcircuitpower باحساسیت گزارششود؛توانGPUباانرژیمخابرهیکی نیست. بودجهتوان وزن‌دار ممکن استintegralityزیرکلاسقبلیراازبینببرد؛ matchingexactفقطباتمامفرض‌هایشاعتباردارد.

کنترل توان پیوسته،ضریب نرخ را تابع متغیرتصمیم می‌کند و عموماًبهMINLP/nonconvexبرمی‌گردد؛حلgridیکILPدقیقبرایهمانgridاست،نهحلglobalمدلپیوسته. بررسیgrid refinement بافرصتخطایمدل جداازLPgap الزامی است. scalarizingpower/rateبایکλنبایدبه‌جایParetofrontمعتبر معرفی شود.

## benchmark اجرایی اولیه پس از پذیرش برنامه

سقفبدوننصب:محیطtf-gpu/CuPy13.6موجود باDLLpathموقت؛CPUreferenceازSciPyموجود؛cuOptنصبنیست،UbuntuWSLداریمولیpythonآنفاقدبستهعلمی است. cuOpt/GurobiGPUبهLinux/WSLوابسته‌اند؛هیچنصبLinuxیاdownloadچندGBدراینpacketنیست. CPUHiGHS برایMILPوLPمرجع؛GPUبرایساختضرایب وPDHG-LPنمونه. این آزمونGPU-MILPexactنیست. امکانcuOptMILPمرحلهبعدباdependency/بودجهجداارزیابی‌شود.

داده:O1_60rows1..100،۴AP×۸آنتن،۳۲زیرحاملواقعی؛خروجیجدا. baselineS02وثبتtestرزروتغییرنکند. channel-array/source/seed/hashثبتشود. توان‌ها[.05,.1,.2]W،P_ref=.2W،noisePSD−174dBm/Hz،NF=7dB،B_total=50MHz،B_s=B_total/32. این‌هافرضسناریو هستند نهپارامتراثبات‌شدهسخت‌افزارمقاله؛سطوحتواندستگاهی ودادهگروهlegacyجداگزارش شوند. نرخهرUEبراساسpowerخودونویزهمانRBمحاسبهشود.

پایلوتbenchmarkمحاسبات:U=8,16,32 باS=U/2،یکseedثبت‌شدهدرهراندازه؛اگرVRAMتخمینی<۴GBوRAMتخمینی<۸GBبودU64نیزفقطیکبار. همهpairها و۹powerprofile،بدونcandidatepruningپنهان. داده ازdevelopmentقدیمی،CSIورودی معلوم برایsolverstudy؛اینمرحلهاثباتpolicyباCSIخطاداریاcoverageنیست. T=200وτ=Uبرایorthogonalpilotتبدیلthroughputصرفاًفرضcost است؛اطلاعاتواقعیپایلوتدرsolver-onlybenchmarkشبیه‌سازینمی‌شود. هزینهcomputeبهصورتlatencyوبreak-evenجدا،تاsymbol-durationمستندشود. افزایشSباعثافزایشBWاشغال‌شده می‌شود؛مقایسهsolverهادرهراندازهBWیکسان واثرscaleباBWگزارش شود.

P_budget=.1Uواطلاعاتgridثابت. baselineها:fixed-power .1W باهمانsolver/قیود؛joint-discrete-power؛heuristicfeasible باهمانبودجه درصورتپیاده‌سازی؛LPfull-familyکران. P-Eهدف۹۵٪throughputیکfixed-powerincumbentشدنیهمانinstanceاست؛هدفderivedگزارش شود،نهQoSبرون‌زایvalidated. الزامQoSperUEوfronthaulدرmodelتعریف‌شده‌اندولیbenchmarkاولفعالنیستند؛نمونهfullnetworkvalidationنیست. نمونه۴UEبرایenumerationکاملتوان+منبع نیزآزمونصحت باشد.

PDHGرویGPUبرایmax qᵀz باAz=b،eᵀz≤B،0≤z≤1. خروجیprimalباresidualبالاترازتولرانس،جوابشدنییاboundپاییننیست. dualcandidateλآزاد،μ≥0ازفرمول U=bᵀλ+Bμ+Σ_j max(0,q_j−(Aᵀλ)_j−μe_j)کرانبالامی‌دهد؛درمحاسباتfloatingpointtoleranceوmarginگزارش شود. GPUupperboundبایددرنمونه‌هاباCPUreferenceسازگارباشد. PDHGبهتنهاییبازیابیصحیحیاگواهILPنمی‌دهد.

## آزمون/بودجه/توقف

قبلrunبزرگ:GPUmatmulواقعی؛coefficientsCPU/GPUدرFP64باتولرانس1e−8relative/absolute؛closedformpairبرابرmatrixsolve؛feasibilitybudget؛P-T: LP≥IP و P-E: LP≤IP؛smallenum؛statusهایtimeout/infeasibleبدونgapساختگی. FP32درصورتاستفادهفقطablationباerrorreported،نهجایگزینخاموشFP64.

هرMILP≤۲۰ثانیه،هرGPU-LP≤۳۰ثانیه،generation≤۱۰دقیقه،کلpacket≤۲۰دقیقه،disk≤۲GB،VRAM≤۴GB/RAM≤۸GB. warmupیکباروجدا؛transfer/setup/iteration/verificationزمان‌سنجیجدا؛CPUthreads/hardwareثبت. بزرگیrunدرfailure/OOMافزایشنیابد. توقفمثبت:solveraccuracyوکاهشزماندراندازهمشخص؛توقفمنفی:عدمconvergenceیاoverheadبالاتر،بدونادعایGPUسریع‌تر. همینسقفبرایهمهمقایسه‌هاقبلrunثبتاست.

مقایسهباpaperها:ابتداscope/tableفرض‌هایهمسان؛curveهایSOTAفقطبعدازreimplementationقابلردیابی. مقاله۲۰۰۸powercontroljointنداردو۲۰۲۵همpowerثابتدارد؛نمی‌تواننتیجهpowercontrolخودرامستقیماًبرتریعددیبرcurveهایآن‌هامعرفیکرد. برایbaselineپیوستهتوان،پسازانتخابمرجعجدا،AO/SCA/WMMSEباlabelstationarysolutionوبودجهبرابربررسیشود؛مقالهجدیدبدونآنمقایسه نهایینشود.

اجازههم‌پوشانی:مرحلهS03GبعدازقبولیCP-PLAN-R02وCP-S02می‌تواندبهعنوانengineering/discoveryکنارS03اجراشود؛هیچکدامتاپذیرشمستقلS03وS03GقفلS04رانمی‌گشاید. افزودنpower/GPUادعایعلمیقبلیراخودکارverifiedنمی‌کند.


### A01 correction: objective-specific certificates and physical units

For P-T (max throughput), LP is an upper bound; a feasible integer schedule is a lower bound. For P-E (min power), LP is a lower bound; a feasible integer schedule is an upper bound. Record gaps with the respective direction; do not use the maximization dual formula for P-E. GPU PDHG in this first packet solves P-T only. P-E is evaluated with CPU LP and MILP. For either direction, floating-point objectives are numerical certificates at reported tolerance, not exact rational proofs.

DeepMIMOv3's installed OFDM constructor divides each path amplitude by sqrt(N_subcarriers). To interpret grid powers as watts on one occupied carrier, the physical frequency response used in this experiment is sqrt(32) times its stored channel. Raytracing already removes scenario transmit power, so do not apply path loss or transmit-power normalization twice. Verify a synthetic single-path case and record these source lines/hash. This convention is an explicit modeling assumption; it does not change S02's historical normalized data or findings.
