// قاعدة بيانات الأنشطة — Master activity database (16 phases). Ported from
// villa-qto with the sequencing fixes: no fire scope (villas), external
// paving/landscaping/lighting late, and handover after as-built submission.

export const PHASES = [
  {
    id: "P01", name: "MOBILIZATION & SITE SETUP", nameAr: "التجهيز وتأسيس الموقع", color: "808080",
    activities: [
      { id: "A001", name: "Site Handover & Setting Out Survey", nameAr: "استلام الموقع والتوقيع المساحي", category: "admin", predecessor: null, lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A002", name: "Hoarding, Fencing & Site Security", nameAr: "التسوير والتحويط وأمن الموقع", category: "admin", predecessor: "A001", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A003", name: "Temporary Services (Water, Power, Drainage)", nameAr: "الخدمات المؤقتة (ماء، كهرباء، صرف)", category: "admin", predecessor: "A001", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A004", name: "Site Office, Stores & Accommodation Setup", nameAr: "مكتب الموقع والمخازن والسكن", category: "admin", predecessor: "A001", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 0.5, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A005", name: "DM/Authority Permits & NOC Submissions", nameAr: "تصاريح البلدية وعدم الممانعة", category: "admin", predecessor: "A001", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 3.0, applicableTo: [], floorMult: false, areaSensitive: false },
    ],
  },
  {
    id: "P02", name: "DEMOLITION (RENOVATION)", nameAr: "الهدم (تجديد)", color: "FF0000",
    activities: [
      { id: "A010", name: "Selective Demolition of Existing Structure", nameAr: "هدم انتقائي للمبنى القائم", category: "structural", predecessor: "A005", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: ["DEMOLITION_ONLY"], floorMult: false, areaSensitive: true },
      { id: "A011", name: "Debris Removal & Site Clearance", nameAr: "إزالة المخلفات وتنظيف الموقع", category: "structural", predecessor: "A010", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: ["DEMOLITION_ONLY"], floorMult: false, areaSensitive: false },
    ],
  },
  {
    id: "P03", name: "SUBSTRUCTURE", nameAr: "الأعمال تحت الأرض", color: "843C0C",
    activities: [
      { id: "A020", name: "Excavation & Earthworks", nameAr: "الحفر والأعمال الترابية", category: "structural", predecessor: "A005", lagDays: 2, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A021", name: "Dewatering System Installation", nameAr: "تركيب نظام نزح المياه", category: "structural", predecessor: "A020", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: ["B+G", "B+G+1", "B+G+2", "B+G+3"], floorMult: false, areaSensitive: false },
      { id: "A022", name: "Dewatering Operation (Continuous)", nameAr: "تشغيل نزح المياه (مستمر)", category: "structural", predecessor: "A021", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 6.0, applicableTo: ["B+G", "B+G+1", "B+G+2", "B+G+3"], floorMult: false, areaSensitive: false },
      { id: "A023", name: "Trimming, Blinding & Lean Concrete (PCC)", nameAr: "التسوية والخرسانة العادية", category: "structural", predecessor: "A020", lagDays: 1, startOffsetDays: 0, durationBaseWeeks: 0.5, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A024", name: "Under-Raft Waterproofing (Bituminous Membrane)", nameAr: "عزل أسفل اللبشة (مشمع بيتوميني)", category: "structural", predecessor: "A023", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A025", name: "Raft Foundation — Reinforcement Steel", nameAr: "اللبشة — حديد التسليح", category: "structural", predecessor: "A024", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A026", name: "Raft Foundation — Formwork & Concrete Pour", nameAr: "اللبشة — القوالب وصب الخرسانة", category: "structural", predecessor: "A025", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.5, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A027", name: "Raft Concrete Curing (Min 7 Days)", nameAr: "معالجة خرسانة اللبشة (٧ أيام)", category: "structural", predecessor: "A026", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A028", name: "Backfilling & Compaction in Layers", nameAr: "الردم والدمك بالطبقات", category: "structural", predecessor: "A027", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A029", name: "Basement Retaining Walls — RC", nameAr: "جدران القبو الساندة — خرسانة مسلحة", category: "structural", predecessor: "A027", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 2.5, applicableTo: ["B+G", "B+G+1", "B+G+2", "B+G+3"], floorMult: false, areaSensitive: true },
      { id: "A030", name: "Basement Slab on Grade", nameAr: "بلاطة أرضية القبو", category: "structural", predecessor: "A029", lagDays: 2, startOffsetDays: 0, durationBaseWeeks: 1.5, applicableTo: ["B+G", "B+G+1", "B+G+2", "B+G+3"], floorMult: false, areaSensitive: true },
    ],
  },
  {
    id: "P04", name: "SUPERSTRUCTURE", nameAr: "الأعمال العلوية", color: "1F3864",
    activities: [
      { id: "A040", name: "Ground Floor — Columns & Shear Walls (RC)", nameAr: "الأرضي — أعمدة وجدران قص", category: "structural", predecessor: "A027", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 1.5, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A041", name: "Ground Floor — Beams & Slab Formwork", nameAr: "الأرضي — كمرات وقوالب السقف", category: "structural", predecessor: "A040", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.5, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A042", name: "Ground Floor — Slab Reinforcement Steel", nameAr: "الأرضي — حديد تسليح السقف", category: "structural", predecessor: "A041", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A043", name: "Ground Floor — Slab Concrete Pour & Cure", nameAr: "الأرضي — صب ومعالجة السقف", category: "structural", predecessor: "A042", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A044", name: "Mezzanine Floor Structure (RC Slab)", nameAr: "هيكل الميزانين (بلاطة خرسانية)", category: "structural", predecessor: "A043", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: ["G+M", "G+M+1", "G+M+2"], floorMult: false, areaSensitive: true },
      { id: "A045", name: "1st Floor — Columns & Shear Walls", nameAr: "الأول — أعمدة وجدران قص", category: "structural", predecessor: "A043", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 1.5, applicableTo: ["G+1", "G+2", "G+3", "G+4", "G+M+1", "G+M+2", "B+G+1", "B+G+2", "B+G+3"], floorMult: false, areaSensitive: true },
      { id: "A046", name: "1st Floor — Beams, Slab Formwork & Concrete", nameAr: "الأول — كمرات وقوالب وصب السقف", category: "structural", predecessor: "A045", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 2.5, applicableTo: ["G+1", "G+2", "G+3", "G+4", "G+M+1", "G+M+2", "B+G+1", "B+G+2", "B+G+3"], floorMult: false, areaSensitive: true },
      { id: "A047", name: "2nd Floor — Columns, Beams, Slab", nameAr: "الثاني — أعمدة وكمرات وسقف", category: "structural", predecessor: "A046", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 3.5, applicableTo: ["G+2", "G+3", "G+4", "G+M+2", "B+G+2", "B+G+3"], floorMult: false, areaSensitive: true },
      { id: "A048", name: "3rd Floor — Columns, Beams, Slab", nameAr: "الثالث — أعمدة وكمرات وسقف", category: "structural", predecessor: "A047", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 3.5, applicableTo: ["G+3", "G+4", "B+G+3"], floorMult: false, areaSensitive: true },
      { id: "A049", name: "4th Floor — Columns, Beams, Slab", nameAr: "الرابع — أعمدة وكمرات وسقف", category: "structural", predecessor: "A048", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 3.5, applicableTo: ["G+4"], floorMult: false, areaSensitive: true },
      { id: "A050", name: "Roof Slab & Water Tank Slab", nameAr: "سقف السطح وبلاطة الخزان", category: "structural", predecessor: "A049", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: [], floorMult: false, areaSensitive: true },
    ],
  },
  {
    id: "P05", name: "BLOCKWORK & MASONRY", nameAr: "أعمال البلوك والمباني", color: "BF8F00",
    activities: [
      { id: "A060", name: "External Block Walls (All Floors)", nameAr: "جدران بلوك خارجية (كل الأدوار)", category: "structural", predecessor: "A050", lagDays: 7, startOffsetDays: 0, durationBaseWeeks: 2.5, applicableTo: [], floorMult: true, areaSensitive: true },
      { id: "A061", name: "Internal Partition Block Walls", nameAr: "جدران بلوك داخلية", category: "structural", predecessor: "A060", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 2.5, applicableTo: [], floorMult: true, areaSensitive: true },
      { id: "A062", name: "Parapet Walls & Coping", nameAr: "دروة السطح والكوبستة", category: "structural", predecessor: "A050", lagDays: 7, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A063", name: "Staircase Blockwork, Precast Steps & Handrails", nameAr: "بلوك الدرج والقلبات والدرابزين", category: "structural", predecessor: "A060", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.5, applicableTo: ["G+1", "G+2", "G+3", "G+4", "G+M", "G+M+1", "G+M+2", "B+G", "B+G+1", "B+G+2", "B+G+3"], floorMult: false, areaSensitive: false },
    ],
  },
  {
    id: "P06", name: "MEP FIRST FIX (ROUGH-IN)", nameAr: "تمديدات كهروميكانيكية أولية", color: "0070C0",
    activities: [
      { id: "A070", name: "Electrical First Fix — Conduits, Cable Trays, DB Boxes", nameAr: "كهرباء أولية — مواسير ومجاري وعلب", category: "mep", predecessor: "A061", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 3.0, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A071", name: "Plumbing First Fix — Water, Drainage & Sewage Piping", nameAr: "سباكة أولية — تغذية وصرف", category: "mep", predecessor: "A061", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 3.0, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A072", name: "AC Ductwork, Piping & Fan Coil Rough-In", nameAr: "تكييف — دكتات ومواسير ووحدات", category: "mep", predecessor: "A061", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 3.0, applicableTo: [], floorMult: false, areaSensitive: true },
    ],
  },
  {
    id: "P07", name: "ROOF WATERPROOFING & INSULATION", nameAr: "عزل السطح والحماية الحرارية", color: "00B0F0",
    activities: [
      { id: "A080", name: "Roof Waterproofing (Torch-On Membrane, 2 Layers)", nameAr: "عزل السطح (مشمع حراري طبقتان)", category: "finishes", predecessor: "A062", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 1.5, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A081", name: "Roof Thermal Insulation (EPS/PIR Board)", nameAr: "عزل حراري للسطح (ألواح)", category: "finishes", predecessor: "A080", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A082", name: "Roof Protection Screed & Drainage Layer", nameAr: "مدة الحماية وطبقة التصريف", category: "finishes", predecessor: "A081", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: true },
    ],
  },
  {
    id: "P08", name: "EXTERNAL ENVELOPE", nameAr: "الغلاف الخارجي", color: "7030A0",
    activities: [
      { id: "A090", name: "Aluminium Window & Door Frame Installation", nameAr: "تركيب إطارات الألمنيوم للنوافذ والأبواب", category: "finishes", predecessor: "A061", lagDays: 5, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A091", name: "Glazing (Glass Installation to All Frames)", nameAr: "تركيب الزجاج لكل الإطارات", category: "finishes", predecessor: "A090", lagDays: 7, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A092", name: "External Cladding / Stone / Feature Elements", nameAr: "تكسية خارجية / حجر / عناصر مميزة", category: "finishes", predecessor: "A091", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A093", name: "External Plaster, Render & Texture Coat", nameAr: "لياسة خارجية وطبقة نسيجية", category: "finishes", predecessor: "A091", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 3.0, applicableTo: [], floorMult: true, areaSensitive: true },
    ],
  },
  {
    id: "P09", name: "INTERNAL PLASTER & SCREEDING", nameAr: "اللياسة الداخلية والمدة", color: "C55A11",
    activities: [
      { id: "A100", name: "Internal Plastering — All Rooms & Corridors", nameAr: "لياسة داخلية — كل الغرف والممرات", category: "finishes", predecessor: "A072", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 3.0, applicableTo: [], floorMult: true, areaSensitive: true },
      { id: "A101", name: "Floor Screeding — All Areas", nameAr: "مدة الأرضيات — كل المناطق", category: "finishes", predecessor: "A100", lagDays: 5, startOffsetDays: 0, durationBaseWeeks: 2.5, applicableTo: [], floorMult: true, areaSensitive: true },
      { id: "A102", name: "Thermal & Sound Insulation (Walls & Ceilings)", nameAr: "عزل حراري وصوتي (جدران وأسقف)", category: "finishes", predecessor: "A100", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: true },
    ],
  },
  {
    id: "P10", name: "WET AREA WATERPROOFING", nameAr: "عزل المناطق الرطبة", color: "2E75B6",
    activities: [
      { id: "A110", name: "Wet Area Waterproofing — Baths, Kitchen, Balconies", nameAr: "عزل المناطق الرطبة — حمامات ومطبخ وشرفات", category: "finishes", predecessor: "A101", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 1.5, applicableTo: [], floorMult: true, areaSensitive: true },
      { id: "A111", name: "Waterproofing Flood Test (Min 48hrs Per Zone)", nameAr: "اختبار الغمر للعزل (٤٨ ساعة لكل منطقة)", category: "finishes", predecessor: "A110", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 0.5, applicableTo: [], floorMult: false, areaSensitive: false },
    ],
  },
  {
    id: "P11", name: "TILING & FLOORING", nameAr: "البلاط والأرضيات", color: "70AD47",
    activities: [
      { id: "A120", name: "Wall Tiling — Baths, Kitchen & Utility Areas", nameAr: "بلاط الجدران — حمامات ومطبخ", category: "finishes", predecessor: "A111", lagDays: 2, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: [], floorMult: true, areaSensitive: true },
      { id: "A121", name: "Floor Tiling — Living, Dining, Bedrooms, Corridors", nameAr: "بلاط الأرضيات — المعيشة والغرف والممرات", category: "finishes", predecessor: "A111", lagDays: 2, startOffsetDays: 0, durationBaseWeeks: 3.0, applicableTo: [], floorMult: true, areaSensitive: true },
      { id: "A122", name: "Marble / Natural Stone Flooring & Skirting", nameAr: "أرضيات رخام / حجر طبيعي وقواعد", category: "finishes", predecessor: "A121", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.5, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A123", name: "Staircase Marble / Tiles & Nosing", nameAr: "رخام / بلاط الدرج والأنوف", category: "finishes", predecessor: "A120", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: ["G+1", "G+2", "G+3", "G+4", "G+M", "G+M+1", "G+M+2", "B+G", "B+G+1", "B+G+2", "B+G+3"], floorMult: false, areaSensitive: false },
    ],
  },
  {
    id: "P12", name: "CARPENTRY & JOINERY (SECOND FIX)", nameAr: "النجارة والديكور (تركيب نهائي)", color: "A9D18E",
    activities: [
      { id: "A130", name: "Internal Door Frames, Solid Core Doors & Ironmongery", nameAr: "أبواب داخلية وإطارات وإكسسوارات", category: "finishes", predecessor: "A120", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: [], floorMult: true, areaSensitive: true },
      { id: "A131", name: "Built-in Wardrobes, Closets & Storage Units", nameAr: "خزائن ودواليب ووحدات تخزين", category: "finishes", predecessor: "A130", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.5, applicableTo: [], floorMult: true, areaSensitive: true },
      { id: "A132", name: "Kitchen Cabinets, Countertops & Island", nameAr: "خزائن المطبخ والأسطح والجزيرة", category: "finishes", predecessor: "A130", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.5, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A133", name: "Decorative Ceilings (Gypsum Board, MDF, Cornices)", nameAr: "أسقف ديكورية (جبس بورد، كرانيش)", category: "finishes", predecessor: "A100", lagDays: 5, startOffsetDays: 0, durationBaseWeeks: 2.5, applicableTo: [], floorMult: true, areaSensitive: true },
      { id: "A134", name: "Ceiling Access Hatches & Boxing", nameAr: "فتحات الخدمة والتغليف للأسقف", category: "finishes", predecessor: "A133", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 0.5, applicableTo: [], floorMult: false, areaSensitive: false },
    ],
  },
  {
    id: "P13", name: "MEP SECOND FIX (FINISHES)", nameAr: "تمديدات كهروميكانيكية نهائية", color: "0070C0",
    activities: [
      { id: "A140", name: "Electrical Second Fix — Switches, Sockets, Panels, LED", nameAr: "كهرباء نهائية — مفاتيح وأفياش ولوحات", category: "mep", predecessor: "A133", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: [], floorMult: true, areaSensitive: true },
      { id: "A141", name: "Plumbing Second Fix — Sanitaryware, Taps, Showers", nameAr: "سباكة نهائية — أدوات صحية وخلاطات", category: "mep", predecessor: "A120", lagDays: 7, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: [], floorMult: true, areaSensitive: true },
      { id: "A142", name: "AC Units, Split Units, Grilles & Diffusers", nameAr: "وحدات التكييف والشبكات والمخارج", category: "mep", predecessor: "A133", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.5, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A143", name: "Generator, DB Board Final Connections & Earthing", nameAr: "المولد واللوحات والتأريض — توصيل نهائي", category: "mep", predecessor: "A140", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 0.5, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A144", name: "Home Automation, CCTV & Intercom System", nameAr: "الأتمتة المنزلية والمراقبة والاتصال", category: "mep", predecessor: "A140", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: false },
    ],
  },
  {
    id: "P14", name: "PAINTING", nameAr: "الدهانات", color: "F4B942",
    activities: [
      { id: "A150", name: "Primer Coat — All Internal Walls & Ceilings", nameAr: "وجه أساس — كل الجدران والأسقف", category: "finishes", predecessor: "A133", lagDays: 5, startOffsetDays: 0, durationBaseWeeks: 1.5, applicableTo: [], floorMult: true, areaSensitive: true },
      { id: "A151", name: "Internal Emulsion Paint — 2nd & 3rd Coats", nameAr: "دهان داخلي — الوجهان الثاني والثالث", category: "finishes", predecessor: "A150", lagDays: 2, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: [], floorMult: true, areaSensitive: true },
      { id: "A152", name: "External Masonry Paint / Texture Coating", nameAr: "دهان خارجي / طبقة نسيجية", category: "finishes", predecessor: "A093", lagDays: 7, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: [], floorMult: true, areaSensitive: true },
    ],
  },
  {
    id: "P15", name: "EXTERNAL WORKS", nameAr: "الأعمال الخارجية", color: "375623",
    activities: [
      { id: "A160", name: "Boundary Wall Construction (Block + Plaster + Coping)", nameAr: "سور الموقع (بلوك + لياسة + كوبستة)", category: "external", predecessor: "A028", lagDays: 7, startOffsetDays: 0, durationBaseWeeks: 3.0, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A161", name: "Main Entrance Gate, Secondary Gate & Fencing", nameAr: "البوابة الرئيسية والفرعية والتسوير", category: "external", predecessor: "A160", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A162", name: "External Paving, Driveway & Parking Area", nameAr: "الرصف الخارجي والممرات والمواقف", category: "external", predecessor: "A152", lagDays: 7, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A163", name: "Soft Landscaping, Irrigation & Planting", nameAr: "تنسيق الحدائق والري والزراعة", category: "external", predecessor: "A162", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: [], floorMult: false, areaSensitive: true },
      { id: "A164", name: "External Lighting, Utilities & Street Furniture", nameAr: "الإنارة الخارجية والخدمات والأثاث", category: "external", predecessor: "A162", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A165", name: "Swimming Pool Structure (RC Shell)", nameAr: "هيكل المسبح (خرسانة مسلحة)", category: "external", predecessor: "A028", lagDays: 14, startOffsetDays: 0, durationBaseWeeks: 4.0, applicableTo: ["POOL"], floorMult: false, areaSensitive: false },
      { id: "A166", name: "Pool Waterproofing, Tiling & Equipment Room", nameAr: "عزل وبلاط المسبح وغرفة المعدات", category: "external", predecessor: "A165", lagDays: 3, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: ["POOL"], floorMult: false, areaSensitive: false },
      { id: "A167", name: "Pool Pump Room, Filtration & Heating Systems", nameAr: "غرفة مضخات المسبح والفلترة والتسخين", category: "mep", predecessor: "A166", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: ["POOL"], floorMult: false, areaSensitive: false },
    ],
  },
  {
    id: "P16", name: "TESTING, COMMISSIONING & HANDOVER", nameAr: "الاختبار والتشغيل والتسليم", color: "C00000",
    activities: [
      { id: "A170", name: "Testing & Commissioning — Electrical Systems", nameAr: "اختبار وتشغيل — الأنظمة الكهربائية", category: "mep", predecessor: "A143", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A171", name: "Testing & Commissioning — Plumbing & Drainage", nameAr: "اختبار وتشغيل — السباكة والصرف", category: "mep", predecessor: "A141", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A172", name: "Testing & Commissioning — AC Systems", nameAr: "اختبار وتشغيل — أنظمة التكييف", category: "mep", predecessor: "A142", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A174", name: "Municipality Final Inspection & Completion Certificate", nameAr: "تفتيش البلدية النهائي وشهادة الإنجاز", category: "admin", predecessor: "A170", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A175", name: "Snagging Survey, Punch List & Rectification Works", nameAr: "حصر الملاحظات وقائمة النواقص وإصلاحها", category: "admin", predecessor: "A174", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 2.0, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A176", name: "As-Built Drawings & O&M Manuals Submission", nameAr: "مخططات كما نُفّذ وأدلة التشغيل والصيانة", category: "admin", predecessor: "A175", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 1.0, applicableTo: [], floorMult: false, areaSensitive: false },
      { id: "A177", name: "Handover & Client Acceptance Certificate", nameAr: "التسليم وشهادة قبول العميل", category: "admin", predecessor: "A176", lagDays: 0, startOffsetDays: 0, durationBaseWeeks: 0.5, applicableTo: [], floorMult: false, areaSensitive: false },
    ],
  },
];

/** Master ordered list of activity ids (used for predecessor fallback). */
export const MASTER_ORDER = PHASES.flatMap((p) => p.activities.map((a) => a.id));

/** Quick lookup of any activity definition by id. */
export const ACTIVITY_BY_ID = Object.fromEntries(
  PHASES.flatMap((p) => p.activities.map((a) => [a.id, a])),
);

export const TOTAL_ACTIVITIES = MASTER_ORDER.length;
