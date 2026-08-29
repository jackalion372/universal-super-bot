EUROPEAN_ACADEMIC_SYSTEM_PROMPT = """
Siz Yevropaning yetakchi universiteti (Oxford/Cambridge/ETH Zurich) professori va tajribali akademik tadqiqotchisiz.
Sizning vazifangiz talaba uchun 100% tayyor, professional, akademik jihatdan asoslangan va o'qituvchi tomonidan AI tomonidan yozilgan deb gumon qilinmaydigan mukammal ish tayyorlashdir.

QAT'IY QOIDALAR VA AKADEMIK STANDARTLAR:
1. SUN'IY INTELLEKT BELGILARINI BATAMOM YO'QOTISH:
   - "Bugungi kunda...", "Zamonaviy dunyoda...", "Shuni ta'kidlash joizki...", "Xulosa qilib aytganda...", "Kelajakda..." kabi sun'iy va trafaret (AI) iboralarni UMUMAN ISHLATMANG.
   - Matnni to'g'ridan-to'g'ri mavzuning ilmiy mantiqiy mohiyatidan va aniq faktlardan boshlang.
   - Keraksiz `---`, `***`, `===` kabi vizual shox-shabbalar va bezakli chiziqlarni ISHLATMANG. Matn faqat professional abzas va sarlavhalardan iborat bo'lsin.

2. YEVROPA ILMIY MANBALARI VA IQTIBOSLAR (VERIFIED REFERENCES):
   - Har bir tadqiqotda nufuzli Yevropa va jahon ilmiy manbalariga (Oxford University Press, Cambridge Academic, Springer, IEEE, Nature, Elsevier, Scopus, Web of Science) va xalqaro ilmiy manbalarga aniq iqtiboslar keltiring.
   - Qalbaki yoki uydirma manbalar yozmang. Asosiy va haqiqiy ilmiy adabiyotlar va nashrlarga tayanib yozing.

3. TAYYOR MAHSULOT STANDARTI:
   - Hujjat shunday darajada mukammal va akademik uslubda shakllantirilsinki, talaba uni o'qituvchisiga topshirganda birorta ham tahrir yoki tuzatish kiritishga ehtiyoj sezmasin.
   - Til adabiy, sof, aniq va ilmiy terminologiyaga boy bo'lsin.
"""

def get_student_prompt(doc_type: str, topic: str, extra_notes: str = "") -> str:
    prompts = {
        "miq": f"""
Mavzu: {topic}
Hujjat turi: Mustaqil Ish (Academic Independent Research Paper)

TUZILISH VA TALABLAR:
1. REJA (Table of Contents)
2. KIRISH (Introduction - Mavzuning dolzarbligi, tadqiqot maqsadi, ilmiy vazifalari)
3. 1-BOB: MAVZUNING NAZARIY ASOSLARI VA YEVROPA ADABIYOTLARI TAHLILI
4. 2-BOB: AMALIY TAHLIL VA MUAMMONING YECHIMLARI
5. XULOSA VA AMALIY TAVSIYALAR
6. FOYDALANILGAN ILMIY ADABIYOTLAR RO'YXATI (Kamida 5-7 ta haqiqiy Yevropa va xalqaro manba)

Qo'shimcha ko'rsatmalar: {extra_notes}
""",
        "ref": f"""
Mavzu: {topic}
Hujjat turi: Akademik Referat (Academic Report)

TUZILISH:
1. Reja
2. Kirish (Dolzarbligi va nazariy ahamiyati)
3. Asosiy qism (Mavzuning chuqur ilmiy tahlili)
4. Xulosa (Aniq xulosaviy fikrlar)
5. Foydalanilgan adabiyotlar (Haqiqiy xalqaro va milliy manbalar)

Qo'shimcha ko'rsatmalar: {extra_notes}
""",
        "kurs": f"""
Mavzu: {topic}
Hujjat turi: Kurs Ishi (Coursework Paper)

TUZILISH:
1. Mundarija
2. Kirish (Mavzuning dolzarbligi, obyekti, predmeti, maqsadi, vazifalari, metodologiyasi)
3. I BOB (Nazariy va konseptual masalalar)
4. II BOB (Tahliliy va amaliy qism)
5. Xulosa va takliflar
6. Foydalanilgan adabiyotlar ro'yxati (APA/IEEE standarti bo'yicha)

Qo'shimcha ko'rsatmalar: {extra_notes}
""",
        "test": f"""
Mavzu: {topic}
Hujjat turi: Akademik Test Savollari (Test Bank)

TALAB:
- 10 ta professional va mantiqiy savol tuzing.
- Har bir savol uchun 4 ta variant (A, B, C, D) taqdim eting.
- Savollar yakunida to'g'ri kalitlarni (Javoblar va qisqa izoh) ilova qiling.

Qo'shimcha ko'rsatmalar: {extra_notes}
""",
        "tezis": f"""
Mavzu: {topic}
Hujjat turi: Ilmiy Tezis (Conference Abstract / Thesis Statement)

TALAB:
- Anjuman va ilmiy jurnallar uchun 1-2 sahifalik ixcham, mazmunli va nufuzli ilmiy tezis.
- Dolzarblik, metodologiya, asosiy natija va xulosa.

Qo me'shimcha ko'rsatmalar: {extra_notes}
""",
        "cross": f"""
Mavzu: {topic}
Hujjat turi: Krossword va Kalit So'zlar

TALAB:
- 10-12 ta tayanch atama va tushunchalar bo'yicha krossword savollari hamda to'g'ri javoblar ro'yxati.
""",
        "maqola": f"""
Mavzu: {topic}
Hujjat turi: Ilmiy-Ommabop Maqola (Academic Article)

TALAB:
- Sarlavha, Annotatsiya (Abstract), Kalit so'zlar (Keywords), Kirish, Asosiy tahlil, Xulosa va Manbalar.
""",
        "insho": f"""
Mavzu: {topic}
Hujjat turi: Adabiy Insho / Esse (Academic Essay)

TALAB:
- Chuqur mantiqiy fikrlar, adabiy til va falsafiy-tahliliy yondashuv.
""",
        "infografika": f"""
Mavzu: {topic}
Hujjat turi: Infografika va Vizual Tuzilma

TALAB:
- Vizual taqdimot uchun bo'limlar, bloklar, statistik ko'rsatkichlar va ierarxik sxemalar strukturasi.
""",
        "sayt": f"""
Mavzu: {topic}
Hujjat turi: Veb-sayt Koda Shablon (HTML / CSS / JS)

TALAB:
- Zamonaviy, responsive va toza HTML5, CSS3 va JavaScript kodi.
"""
    }
    return prompts.get(doc_type, f"Mavzu: {topic}\nHujjat turi: {doc_type}\n{extra_notes}")
