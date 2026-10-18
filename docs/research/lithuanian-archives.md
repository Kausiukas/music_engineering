# Lithuanian archives: access and terms (T0, issue #17)

- Date: 2026-10-18
- Question (issue #17): Which Lithuanian archives give access, and on what terms?
- Scope: gold-standard test items for the reverse-engineering app: a recording of a Lithuanian song paired with notated melody (sheet music or MIDI) and lyrics, ideally word-timed. Approved professional musicians review every item. Secondary: open Lithuanian speech data for the voice pipeline.
- Method: official institution pages and repository records, opened on 2026-10-18. Anything marked **unverified** was not confirmed on a page we opened. No source gives us a licence for derived/test use in writing; every archive below still needs that question asked explicitly.

## Recommendation

Approach these first, in this order:

1. **LLTI Lithuanian Folklore Archives, phonograph collection (LTRF v / LTRF pl).** The only source found that already pairs audio with notation: each disc record lists the archive *text* collection number and *melody* collection number for the same performance, plus the melody transcriber (e.g. LTRF pl 966 → text LTR 1650/6, melody LTR 2855/17, transcribed by Juozas Jurga). About 6,700 disc items (1935–1949) and 340 cylinder items (1908–1949) are digitized and listenable online. Paired notation must be ordered as scans. Terms: copying needs written permission from the Institute's director with a stated purpose; paid per item (audio 0.50 EUR/min MP3, 1.00 EUR/min WAV; scans 0.30–3.50 EUR/page; search 14–28 EUR/h); up to 70% discount for Lithuanian research/teaching. Recordings are 80+ years old, so performer rights have likely lapsed (**unverified**, legal check needed); the transcriptions and the archive's own terms are what we must negotiate. Weak point: old, noisy, mono, unaccompanied field recordings, so they test the hard end, not the typical input.
2. **Lithuanian National Culture Centre (LNKC, formerly LLKC) Folk Creation Archive and its publication series.** 3,000+ audio/video recordings, 200+ manuscript collections, and published series *Dainos iš visos Lietuvos* (15 volumes) and *Lietuvių liaudies instrumentinė muzika* (9 volumes). Terms are set case by case "depending on the scope and purpose", granted on a written request (LT/EN forms). Pairing with notation is **unverified**; worth asking because its recordings are newer (1990+) and cleaner than LLTI's phonographs and it publishes songbooks.
3. **Music Information Centre Lithuania (MICL).** Not for folk material but the strongest notation source for composed Lithuanian music: ~6,000 manuscript scores/parts, ~5,000 published scores, 7,600+ unreleased recordings and ~2,300 releases. Scores scanned for a flat fee (3–10 EUR per work by page count); materials are "free for promotional use" with attribution. Unreleased recordings can only be heard on site, and most works are in copyright (living or recent composers), so test use needs per-work permission. Best for choral works where we can match a published score to a released recording.

Use for the voice pipeline (not gold-standard songs): **LIEPA-3** (CC BY 4.0, 10,000 h, word/phoneme timing for 500 h) and **Common Voice lt** (CC0, ~28 h validated; figures from search listing, **unverified**).

## Comparison

| Source | Audio | Notation | Lyrics | Timing | Format / size | Access | Terms | Fit |
|---|---|---|---|---|---|---|---|---|
| LLTI phonograph collection (LTRF v, LTRF pl) | Yes, online player | Yes, archive melody transcriptions referenced per record (scans on order) | Yes, text transcriptions referenced per record | No | 117 cylinders / 340 items; ~980 discs / 6,700+ items; digitized | Online listening at irasai.archyvas.llti.lt; copies by written request | Director's written permission; paid copies; no reuse licence stated | **High** |
| LLTI tapes and cassettes (LTRF mg) | Yes, 8,500+ h; only resistance-songs subset (1,197 items) and some metadata online | Some in manuscripts (**unverified** per item) | Partial (many items "not transcribed") | No | Tapes 1952–1994, cassettes 1971–2015 | Reading room or paid copy | As above | Medium |
| LLTI manuscript database (tautosakos-rankrastynas.lt) | Links to audio DB | Yes, "natos" document type; melody collections | Yes, 2M+ items | No | Scanned manuscripts + descriptions | Online, no registration seen | Only "© LLTI" footer | Medium (notation side of pairs) |
| LNKC (ex-LLKC) archive and publications | 3,000+ recordings; 500+ folklore records 1968–2010 | **Unverified** | Manuscripts | No | Tapes; CD series | Written request (LT/EN form) | Case by case, fees by scope/purpose | Medium |
| MICL score library | 7,600+ unreleased (on site only), 2,300 releases | ~6,000 manuscripts, ~5,000 published scores | In vocal scores | No | Paper/PDF scans; CDs | Scans 3–10 EUR; borrow/rent; shop | Free for promotional use with credit; copyright per work | Medium |
| epaveldas.lt (LNB aggregator) | Shellac records, piano rolls | Not stated | No | No | 280,000+ objects, 24 institutions | Online | Every object carries a CC licence/rights label | Medium (audio side; check per object) |
| LNB music collections ("Senoji plokštelė") | Largest old-record collection in LT; digitized shellac (project since 2003) | Sheet music not confirmed | No | No | Count not stated | Reading room; Facebook clips | LNB's own data CC BY; third-party items per object | Low–medium |
| LMTA library | 59,000 audio/video items (+ licensed DBs for staff/students) | 156,000+ sheet-music items | In scores | No | Physical; virtual catalogue vb.lmta.lt | External access **unverified** | Not stated | Low–medium |
| LRT archive | Radio/TV archive (size **unverified**) | No | No | No | **Unverified** | Licence agreements via LRT archive department | Commercial licensing (prices **unverified**) | Low |
| LIEPA-3 (CLARIN-LT) | 10,000 h speech, 100 h dialects, no singing | No | Transcripts | Phrase-level all; word/phoneme for 500 h (TextGrid) | FLAC 44.1 kHz/16-bit; 1.13 TB | Direct download | CC BY 4.0 | High for voice pipeline, none for songs |
| Common Voice lt (Mozilla Data Collective) | ~35 h read speech, 331 speakers (**unverified**) | No | Prompts | No | Clips | MDC account (**unverified**) | CC0; no re-hosting, no speaker identification (**unverified**) | Medium for voice pipeline |

No open dataset of Lithuanian *sung* audio with aligned notation or word timing was found.

## Notes per source

### LLTI (Institute of Lithuanian Literature and Folklore), Lithuanian Folklore Archives
- Holdings: 2M+ folklore items in manuscripts, 400,000+ audio/video recordings, 50,000+ photos (manuscript database front page).
- Phonograph collection: cylinders (1908–1949, 117 surviving / 340 items) and discs (1935–1949, ~980 surviving / 6,700+ items), digitized under a 2001 programme, on the UNESCO Memory of the World national register (2008). Sound + metadata online for LTRF v and LTRF pl; tapes LTRF mg 1–1963 metadata only.
- Selected recordings published with CDs (Suvalkija 2003, Aukštaitija 2004, Žemaitija and Dzūkija 2005); the Dzūkija book is cited as the published source for item LTRF pl 966. These books likely print the melody transcriptions next to the CD audio (**unverified**), which would be the cheapest route to ready pairs.
- Terms (services page): written permission from the director; state purpose; request form `Prašymas dėl naudojimosi archyvu su įsipareigojimais.doc` to archive@llti.lt; prepayment; copies within 10 working days. Already-digitized or published items "are not copied" by the copy service, so ask how online items are licensed for reuse. A Lithuanian PDF of usage rules is linked from the visitor page but we could not open it (**unverified** content).
- Contact: archive@llti.lt, +370 5 262 58 92, Antakalnio g. 6, Vilnius. Head of department Asta Skujytė-Razmienė (astars@llti.lt). Audio DB corrections: irena@llti.lt.

### LNKC (Lithuanian National Culture Centre; Lithuanian Folk Culture Centre until 5 Oct 2016)
- Archive founded 1990; holdings listed above; publication series *Dainos iš visos Lietuvos* since 1999.
- Terms: "usage conditions and prices are set according to the scope and purpose of the material required"; permission on written request.
- Contact: Povilas Laužadis, povilas.lauzadis@lnkc.lt, +370 5 262 6155; lnkc@lnkc.lt. Old domain llkc.lt refused connections.

### MICL (mic.lt)
- Holdings and prices as above; database sections for classical, jazz, pop and folk; shop at musiclithuania.com.
- Contact: info@mic.lt, +370 5 272 6986, A. Mickevičiaus g. 29, Vilnius.

### epaveldas.lt and LNB
- ePaveldas: 280,000+ objects from 24 institutions incl. digitized audio (piano rolls, shellac records); all objects marked with CC licences, the most open allowing derivatives. The portal itself is a JS app we could not read; per-object rights must be checked item by item.
- LNB copyright page: LNB's own descriptions and photos CC BY unless marked otherwise; third-party items may be in copyright or public domain.
- Shellac digitization project (Music Department, since 2003) on the UNESCO national register 2007; record count not stated. Contact biblio@lnb.lt.

### LMTA library
- 309,000 items: 156,000+ sheet music, 59,000 audio/video; catalogue vb.lmta.lt; contact biblioteka@lmta.lt. Terms for external users not found (**unverified**).

### LRT
- Public mediateka shows current programmes only. A job posting confirms LRT's archive department licenses audio and audiovisual archive material under licence agreements. The virtual radio audio library lrvab.lrt.lt refused connections. Prices and folk-music holdings **unverified**.

### Speech corpora
- LIEPA-3: Vilnius University, Vytautas Magnus University, Institute of the Lithuanian Language (2026); handle hdl.handle.net/20.500.11821/101; CC BY 4.0; read 5,000 h, spontaneous 4,900 h, dialects 100 h.
- Common Voice lt: since Oct 2025 distributed only via Mozilla Data Collective (HF card). MDC pages did not render; hours and terms come from search snippets only (**unverified**).

## Sources (opened 2026-10-18)

- LLTI visitor information: https://archyvas.llti.lt/en/articles/information_for_visitors
- LLTI services and prices: https://archyvas.llti.lt/lt/paslaugos/
- LLTI upload materials: https://archyvas.llti.lt/en/upload-materials
- LLTI folklore sound recordings database: https://irasai.archyvas.llti.lt/?lang=en
- LLTI phonogram item LTRF pl 966: https://archyvas.llti.lt/en/lithuanian_folk_music_phonogram_collection?id=60783
- LLTI resistance-songs item LTRF mg 3911: https://archyvas.llti.lt/en/recordings_of_post_wwii_resistance_fighters_songs?id=23567
- LLTI sound archive publication programme: https://agi.archyvas.llti.lt/index_en.html
- LLTI manuscript database: https://www.tautosakos-rankrastynas.lt/ and https://www.tautosakos-rankrastynas.lt/en/
- LNKC archive: https://www.lnkc.lt/archyvas/ ; LNKC home: https://www.lnkc.lt/
- LNKC encyclopedia entry: https://www.vle.lt/straipsnis/lietuvos-nacionalinis-kulturos-centras/
- MICL about: https://www.mic.lt/en/about-us/ ; MICL home: https://www.mic.lt/en
- LNB home: https://www.lnb.lt/ ; ePaveldas description: https://www.lnb.lt/istekliai/duomenu-bazes/lietuvos-kulturos-paveldo-portalas-e-paveldas
- LNB copyright: https://www.lnb.lt/autoriu-teises-publikuojamu-duomenu-naudojimas
- LNB Senoji plokštelė: https://www.lnb.lt/istekliai/kiti-istekliai/senoji-plokstele
- LNB shellac digitization article: https://www.lituanistika.lt/content/20779
- LMTA library: https://biblioteka.lmta.lt/en/
- LRT mediateka: https://www.lrt.lt/mediateka ; LRT archive job posting: https://www.cvbankas.lt/vadybininkas-e-archyvu-skyriuje-vilniuje/1-14104353
- LIEPA-3: https://clarin-repo.lt/items/0a04648e-ba4e-4e6f-9161-a2d01e8e9fdb
- Common Voice on HF (distribution note): https://huggingface.co/datasets/mozilla-foundation/common_voice_17_0

Tried but unreadable: epaveldas.lt (JS shell), llkc.lt and lrvab.lrt.lt (connection refused), mozilladatacollective.com dataset pages (did not render).
