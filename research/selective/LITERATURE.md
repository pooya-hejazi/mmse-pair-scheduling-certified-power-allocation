# غربال پیشینه با محور مدل ترکیبی و بهینه‌سازی

تاریخ:۲۰۲۶/۱۰/۳۰. این مرور هدفمند است و ادعای جامعیت ندارد. جست‌وجوی صرفِ channel estimation کنار گذاشته شد؛ محور joint probing/scheduling، pairing، LP relaxation و قابلیت بازیابی جواب صحیح است.

| منبع اولیه | شواهد خوانده‌شده و اثر بر ادعا |
|---|---|
| [Zhou, Fan, Guo: Joint Channel Probing and Proportional Fair Scheduling، arXiv1009.2602](https://arxiv.org/abs/1009.2602) | متن مدل و قضیه۱/الگوریتم۱: probing هزینه زمانی دارد و با scheduling مشترک بهینه می‌شود؛ مدل تک‌کاربر در هر slot و فرض نرخ‌های همگن نرمال‌شده دارد. بنابراین «انتخاب اطلاعات برای scheduling» به‌تنهایی نوآوری نیست. انتقال optimal stopping آن به گروه‌های تداخلی چندکاربره اثبات می‌خواهد. |
| [Distributed Opportunistic Scheduling With Two-Level Probing، MERL](https://merl.com/publications/TR2009-015) | چکیده ناشر/نهاد پژوهشی: تخمین دقیق‌تر با هزینه probe و throughput مبادله می‌شود؛ مطالعه توقف بهینه با اطلاعات ناقص از قبل وجود دارد. PDF کامل این منبع در این دور بررسی نشد؛ نتیجه فنی فراتر از همین دامنه نقل نمی‌شود. |
| [Sedaghat & Müller: On User Pairing in NOMA Uplink، arXiv1707.01846](https://arxiv.org/abs/1707.01846) | متن بخش معرفی/مدل و تفکیک سناریوها خوانده شد: روش چندجمله‌ایِ suboptimal برای چندزیرحامل، و نتایج exact در سناریوهای محدود single-subcarrier/SIC مطرح است. خود مقاله میان این‌ها فرق می‌گذارد. برچسب pairing یا polynomial به‌تنهایی سهم تازه نیست؛ گیرنده و وابستگی به RB باید دقیق مقایسه شوند. |
| [Hmayed & Bastami: Scalable Cell-Free Massive MIMO System: Joint Optimal Pilot and Access Point Assignment، IEEE Access2025](https://doi.org/10.1109/ACCESS.2025.3638655) | متن نمایه‌شده ناشر درباره BCD، LPهای زیرمسئله و الگوریتم دیده شد؛ دسترسی مستقیم PDF/صفحه با مانع مواجه شد. از snippet نمی‌توان صحت فرمول‌بندی یا exactness را پذیرفت. تفکیک polynomial بودن iteration با optimum کلی از مهم‌ترین موارد بررسی PDF است. **اولویت۱ دریافت از کاربر**. |
| [Optimal User Pairing for Multiuser MIMO، ISSSTA2008](https://engit.monash.edu/profiles/wp-content/uploads/2017/09/isssta08b.pdf) | منبع نویسنده در جست‌وجو یافت شد؛ دریافت PDF timeout شد. چکیده درباره pairing با ML/MMSE و assignment است و از نزدیک‌ترین پیشینه‌هاست. بدون PDF هنوز هیچ حکم درباره یکسانی قضیه این پروژه با آن نداریم. **اولویت۲ دریافت از کاربر**. |
| [Abanto-Leon & Maghsudi: Resilient Full-Duplex ISAC…، arXiv2510.15810v2](https://arxiv.org/pdf/2510.15810v2) | PDF، مدل/مقدمه: reformulation از MINLP به MILP برای تخصیص زمان/beam است؛ متغیرهای صحیح حذف نمی‌شوند. «خطی‌سازی» با «LP دقیقِ چندجمله‌ای» یکسان نیست. دامنه آن single-user ISAC است، نه مدل گروه‌بندی حاضر. |

منابع دور قبل در research/innovation/CLAIMS.md همچنان مرتبط‌اند: Kang2021 برای توقف پایلوت، Li2026 برای conformal gap، SCAN-BEST برای beam selection دارای کنترل ریسک، Amiri2025 برای challenger sampling. هیچ تضمین آن‌ها بدون فرض‌های متناظر به این مسئله منتقل نشده است.

## ادعاهای مجاز و نامجاز در این مرحله

- اجراشده: LMMSE ثابت؛ ارزیابی۱۸زمینه و prototype علّی یک‌probe با همان انرژی/زمان پایلوت؛ LP عادی، enumeration صحیح و witness فیزیکی شکاف.
- اثبات محلی ارائه‌شده: hull دقیق چهارUE/دوRB با قیود مکمل؛ زیرخانواده متعامد با objective جمع‌پذیر و assignment LP؛ کران perturbation مبتنی بر interaction loss. این‌ها هنوز ممیزی مستقل مرحله و غربال کامل novelty نشده‌اند؛ اجزای ریاضی استانداردند.
- ادعای ناموجه: حل عمومی NP-hard با LP، تضمین بهینگی کل سیاست اطلاعات، novelty صرف ترکیب estimator با scheduling، یا برتری end-to-end بدون زمان محاسبه.
- تصمیم: prototype انتخابی فعلاً مبنای claim اصلی نیست. تمرکز ادامه بر شرایط integrality/شکاف و کاربرد آن در تصمیم «LP کافی / حل صحیح / اطلاعات بیشتر» باشد. روش تخمین جدید توسعه داده نشود.

گام بعد از PDFهای نزدیک: مقایسه قیدبه‌قید objective، comparator، fixed pairing دربرابر joint pairing/resource، کانال flat دربرابر selective و نوع گیرنده؛ سپس تعیین اینکه نتیجه ساختاری حاضر تکرار است یا پایه‌ای برای یک بسط مفید. تا آن زمان وضعیت novelty=UNRESOLVED.
