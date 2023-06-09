#TODO: Change phone number prefix

import fitz
import re
from typing import List, Dict
import json

DUPLICATES = []


def convert_phone_nr(nr: str) -> str:
    """Add +49 prefix to phone number and define a custom delimiter"""
    if len(nr) == 0:
        return ""
    _nr = f"+49{nr[1:]}"
    delimiter = "/"
    _nr = delimiter.join(_nr.split("-"))
    return _nr


def fill_telephone_buffer(buffer: List[str]):
    """If either phone nr oder telefax nr is missing in list it will be appended"""
    filled_items = []
    missing_item = ""
    if len(buffer) == 0:
        return ["Telefon:", "Telefax:"]
    for item in buffer:
        if item.startswith("Telefon:"):
            if missing_item == "Telefax:":
                filled_items.append("Telefax:")
            filled_items.append(item)
            missing_item = "Telefax:"
        elif item.startswith("Telefax:"):
            if missing_item == "Telefon:":
                filled_items.append("Telefon:")
            filled_items.append(item)
            missing_item = "Telefon:"
    if filled_items[-1].startswith("Telefon:"):
        filled_items.append("Telefax:")
    return filled_items


def parse_block(block: str) -> Dict:
    """This function categorizes the stream of strings into a python dict"""
    _result = {}
    lines = [line.strip() for line in block.split("\n")]
    # BSNR and LANR are always in the first line and can be extracted statically
    bsnr_line = [line.strip().split(": ") for line in lines[0].split(";")]
    _result[bsnr_line[0][0]] = bsnr_line[0][1]
    _result[bsnr_line[1][0]] = bsnr_line[1][1]
    lines.pop(0)

    # Get name and title of physician from 2-4 row
    _result["Vorname"] = lines[0].split(", ")[1].replace("[A]", "").strip()
    _result["Nachname"] = lines[0].split(", ")[0]
    lines.pop(0)

    # If physician has no title sometimes the next row is an empty string, sometimes it's the description of the practice
    if lines[0].startswith(" ") \
            or lines[0].startswith("Örtliche") \
            or lines[0].startswith("Überörtliche") \
            or lines[0].startswith("Medizinisches") \
            or lines[0].startswith("An") \
            or lines[0].startswith("BS oder NBS einer KV-übergreifende") \
            or lines[0].startswith("MVZ u. gleichz. BS o. NBS einer"):
        _result["Titel"] = ""
    else:
        _result["Titel"] = lines[0]
    lines.pop(0)
    # The address lines are matched by finding the city code via regex (5-digit number)
    regex = r"\b\d{5}\b\s\b"
    address_found = False
    phone_buffer = []
    last_phone_index = None
    _result["Nebenbetriebsstätten"] = []
    _result["Fachgebiete"] = []
    for index, line in enumerate(lines):
        if re.search(regex, line) is not None:
            # When finding city code we start 2 lines above, if possible
            start_index = index - 2 if index >= 2 else 0
            # Sometimes the first row does not contain the street name. Skip to next line
            if lines[start_index].startswith("Nebenbetriebsstätte:"):
                start_index += 2
            elif re.match(r"\d", lines[start_index]):
                start_index += 1
            street_string = " ".join([line.strip() for line in lines[start_index:index]])
            # Remove whitespace if there is a suffix to street nr
            if re.search(r"\s\D+$", street_string) is not None:
                street_string = "".join(street_string.rsplit(" ", 1))
            if not address_found:
                _result["Strasse"] = street_string.strip()
                _result["PLZ"] = line.split(" ")[0]
                _result["Ort"] = line.split(" ")[1]
                address_found = True
            # When finding a 2nd or consecutive city code it belongs to a Nebenbetriebtsstätte
            else:
                _result["Nebenbetriebsstätten"].append({
                    "BSNR": lines[start_index - 1],
                    "Strasse": street_string,
                    "PLZ": line.split(" ")[0],
                    "Ort": line.split(" ")[1],
                    "Telefon": "",
                    "Telefax": ""})
        elif line.startswith("Telefon:") or line.startswith("Telefax:"):
            phone_buffer.append(line)
            last_phone_index = index
        # dirty hack to join specialty names if they span more than one line
        elif re.match(r"\D", line) is not None and last_phone_index is not None:
            if len(_result["Fachgebiete"]) > 0 and \
                    (line.startswith("Arzt")
                     or line.startswith("(KV)")
                     or line.startswith("Hörstörungen")
                     or line.startswith("Geschlechts-Krankheiten")
                     or line.startswith("Hals-Nasen-Ohren-Chirurgie")
                     or line.startswith("Rettungsdienstgesetzen")
                     or line.startswith("Länder")
                     or line.startswith("Kardiologie")
                     or line.startswith("Gastroenterologie")
                     or line.startswith("Intensivmedizin")
                     or line.startswith("Medizinische Genetik")
                     or line.startswith("und Ästhetische")
                     or line.startswith("((M-)WBO 1992/2003)")
                     or line.startswith("Angiologie")
                     or line.startswith("Hämatologie und Onkologie")
                     or line.startswith("Pneumologie")
                     or line.startswith("Nephrologie")
                     or line.startswith("Rettungsdienst gemäß")
                     or line.startswith("-Onkologie*")
                     or line.startswith("und Jugendliche")
                     or line.startswith("(Einzel- und Gruppentherapie)")
                     or line.startswith("(Einzeltherapie)")
                     or line.startswith("und Jugendliche")
                     or line.startswith("analytische Psychotherapie")
                     or line.startswith("für Kinder und Jugendliche")
                     or line.startswith("Jugendlichen-Psychotherapie")
                     or line.startswith("Eintragungsvoraussetzung ")
                     or line.startswith("f.d.approbierten Kinder-")
                     or line.startswith("u.Jug.Psychotherapeuten")
                     or line.startswith("Infektionsepidemiologie")
                     or line.startswith("Gesichts-Chirurgie")
                     or line.startswith("Grundversorgung")
                     or line.startswith("Geburtshilfe")
                     or line.startswith("Psychotherapie (Einzel- und Gruppentherapie)")
                     or line.startswith("Psychotherapie (Einzeltherapie)")
                     or line.startswith("f.d.approbierten")
                     or line.startswith("Psychol.Psychotherapeuten")
                     or line.startswith("Psychotherapie")
                     or line.startswith("Psychother.")
                     or line.startswith("Zulassungsvoraussetzung §95(10)")
                     or line.startswith("f.d. approbierten Psychol.Psychotherapeuten")
                     or line.startswith("Diagnostik Stufe 2 und Therapie")
                     or line.startswith("(gem. Anlage I Nr. 19 § 6 Abs. 2)")
                     or line.startswith("Skelett; kammerindividuell")
                     or line.startswith("Jugendliche")
                     or line.startswith("Kinder und Jugendliche")
                     or line.startswith("Diagnostik (gem. § 2 Abs. 1")
                     or line.startswith("Qualitätssicherungsvereinbarung")
                     or line.startswith("kammerindividuell, Alle")
                     or line.startswith("Fachgebiete")
                     or line.startswith("hirnversorgenden Gefäße, Innere")
                     or line.startswith("Medizin")
                     or line.startswith("u.-psychotherapie")
                     or line.startswith("Eingriffe an der Wirbelsäule")
                     or line.startswith("fachgebunden*")
                     or line.startswith("Balneologie*")
                     or line.startswith("Kardiologie")
                     or line.startswith("Ohren-Heilkunde")):
                _result["Fachgebiete"][-1] += f" {line}"
            else:
                _result["Fachgebiete"].append(line)
    phone_buffer = fill_telephone_buffer(phone_buffer)
    for nr in range(0, int(len(phone_buffer) / 2)):
        if nr > 0:
            try:
                _result["Nebenbetriebsstätten"][nr - 1]["Telefon"] = convert_phone_nr(phone_buffer.pop(0).split(":")[1].strip())
                _result["Nebenbetriebsstätten"][nr - 1]["Telefax"] = convert_phone_nr(phone_buffer.pop(0).split(":")[1].strip())
            except IndexError:
                pass
        else:
            _result["Telefon"] = convert_phone_nr(phone_buffer.pop(0).split(":")[1].strip())
            _result["Telefax"] = convert_phone_nr(phone_buffer.pop(0).split(":")[1].strip())
    return _result


def parse_page(page) -> List:
    _result = []
    # We draw a rectangle over the single entries in the pdf page. Orientation points are the BSNR strings. If an entry
    # is longer than one pdf page we might miss some information on Nebenbetriebsstätten. These have to be corrected
    # manually
    delimiter = page.search_for("BSNR")
    for index, pos in enumerate(delimiter):
        start_x = pos[0]
        start_y = pos[1]
        end_x = 832
        end_y = delimiter[index + 1][1] if index + 1 < len(delimiter) else 549
        _rect = fitz.Rect(start_x, start_y, end_x, end_y)
        text = page.get_textbox(_rect)
        block = parse_block(text)
        global DUPLICATES
        if (block["LANR"], block["BSNR"]) not in DUPLICATES:
            _result.append(block)
            DUPLICATES.append((block["LANR"], block["BSNR"]))
        else:
            print(block)
    return _result


def main():
    for city in ["bremen", "bremerhaven"]:
        doc = fitz.open(f"gesamt_{city}.pdf")
        final_result = []

        # Select only a single page
        # page = doc[5]  # we want text from this page
        # parse_page(page)
        # exit(0)

        for page in doc:
            final_result.extend(parse_page(page))

        # New entry for every Nebenbetriebsstätte
        nbs_list = []
        for _dict in final_result:
            if len(_dict["Nebenbetriebsstätten"]) > 0:
                for nbs in _dict["Nebenbetriebsstätten"]:
                    if nbs['BSNR'] != _dict['BSNR']:
                        _new_entry = {'BSNR': nbs['BSNR'],
                                      'LANR': _dict['LANR'],
                                      'Vorname': _dict['Vorname'],
                                      'Nachname': _dict['Nachname'],
                                      'Titel': _dict['Titel'],
                                      'Fachgebiete': _dict['Fachgebiete'],
                                      'Strasse': nbs['Strasse'],
                                      'PLZ': nbs['PLZ'],
                                      'Ort': nbs['Ort'],
                                      'Telefon': nbs['Telefon'],
                                      'Telefax': nbs['Telefax']}
                        nbs_list.append(_new_entry)
            del _dict["Nebenbetriebsstätten"]

        final_result.extend(nbs_list)

        with open(f"zuweiser_liste_{city}.json", "w", encoding="UTF-8-sig") as file:
            json.dump(final_result, file, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
