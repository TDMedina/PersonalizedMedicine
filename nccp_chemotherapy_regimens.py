
import re
from urllib.request import Request, urlopen
from urllib.parse import urljoin
from warnings import warn

import pandas as pd
from bs4 import BeautifulSoup, Tag

BASE_URL = "https://www.hse.ie/"
CODE_PATTERN = re.compile(r"(P0|P|0)0\d{3}[a-z]?")


def get_chemoprotocol_urls():
    soup = soupify_page(BASE_URL + "/eng/services/list/5/cancer/profinfo/chemoprotocols/")
    spanner = soup.find_all(name="span", class_=False,
                            string="NCCP National SACT Regimens")[0]
    urls = spanner.next.next.find_all(name="a")
    urls = [urljoin(BASE_URL, url["href"]).replace(" ", "%20") for url in urls]
    return urls


def parse_tables_from_all_urls(url_list):
    parsed = {}
    for url in url_list:
        parsed[url] = parse_tables_from_url(url)
    return parsed


def parse_tables_from_url(url):
    parsed = []
    tables = find_tables(soupify_page(url))
    for table in tables:
        content, caption = parse_table(table)
        parsed.append((caption, content))
    return parsed


def soupify_page(url):
    soup = BeautifulSoup(urlopen(Request(url)), "html.parser")
    return soup


def find_tables(soup_obj: BeautifulSoup):
    tables = soup_obj.find_all("table")
    return tables


def parse_table(table_tag: Tag):
    header_re = re.compile("^Regimen(.Name)?")

    caption = table_tag.find("caption")
    if caption is not None:
        caption = caption.text.strip()

    parsed = []
    rows = table_tag.find_all("tr")
    for i, row in enumerate(rows):
        if i == 0 and (row.find(string=header_re) or row.parent.name == "thead"):
            continue
        cols = row.find_all("td")
        if len(cols) != 2:
            warn(f"Weird row: {row}")
            continue

        regimen, indications = cols
        regimen_name, regimen_link = parse_regimen(regimen)
        if regimen_name is None:
            continue
        indics = parse_indications(indications)

        parsed.append((regimen_name, regimen_link, indics))
    return parsed, caption


def parse_regimen(regimen_td_tag):
    name_results = regimen_td_tag.find_all("strong")
    if not name_results:
        return None, None
    # if len(name_results) > 1:
    #     warn(f"Multiple regimen names found: {name_results}")
    regimen_name = name_results[0].string
    if regimen_name is None:
        regimen_name = re.sub("</?.+?>", "", str(name_results[0]))

    regimen_link = regimen_td_tag.find_all("a")
    # if len(regimen_link) > 1:
    #     warn(f"Multiple regimen links found: {regimen_link}")
    regimen_link = regimen_link[0]["href"]
    regimen_link = urljoin(BASE_URL, regimen_link)
    return regimen_name, regimen_link


def parse_indications(indication_td_tag):
    indics = {}
    entries = list(indication_td_tag.find_all("p"))
    current_id = None
    for entry in entries:
        if (code_search := re.search(CODE_PATTERN, str(entry))) and entry.find("strong"):
            current_id = code_search[0]
            indics[current_id] = ""
            continue
        # if bold := entry.find("strong"):
        #     if not bold.string:
        #         continue
        #     if not bold.string == entry.string:
        #         continue
        #     current_id = str(entry.string).strip("*").strip()
        #     indics[current_id] = ""
        #     continue
        if current_id not in indics:
            warn(f"Skipped indication: '{current_id}' in entry: '{entry}'",
                 category=RuntimeWarning)
            # print(indication_td_tag)
            # print("------")
            continue
        desc = str(entry)
        desc = re.sub(r"\xa0", " ", desc)
        desc = re.sub(r"(<.+?>|</.+?>)", "", desc)
        desc = desc.strip()
        if not desc.endswith("."):
            desc += "."
        indics[current_id] += desc
    return indics


def organize_parsed_tables(parsed_data, harmonization_file=None):
    if harmonization_file is not None:
        harmonization_dict = read_harmonization_file(harmonization_file)
    else:
        harmonization_dict = None
    all_regimens = {}
    all_indications = {}
    for url, tables in parsed_data.items():
        name = url.rstrip("/").rsplit("/")[-1]
        name = re.sub(r"%20", " ", name)
        for table_name, table in tables:
            disease = {name}
            if table_name:
                table_name = re.sub(r"\n.+", "", table_name)
                disease.add(f"{name}:{table_name}")
            for entry in table:
                reg_name = fix_regimen_name(entry[0], harmonization_dict)
                if reg_name not in all_regimens:
                    drug_regimen = Regimen(reg_name)
                    all_regimens[reg_name] = drug_regimen
                else:
                    drug_regimen = all_regimens[reg_name]
                drug_regimen.diseases |= disease
                source_url = entry[1]
                indications = entry[2]
                for code, desc in indications.items():
                    if code in all_indications:
                        indication = all_indications[code]
                        if indication.description != desc:
                            if (indication.description.lower().replace(" ", "") ==
                                    desc.lower().replace(" ", "")):
                                pass
                            elif not indication.description:
                                indication.description = desc
                            else:
                                warn(f"Indication description mismatch in indication {code}:"
                                     f"\n1:  {indication.description}"
                                     f"\n2:  {desc}")
                                indication.description += f"\n{desc}"
                        indication.regimens.add(drug_regimen)
                        indication.diseases |= disease
                    else:
                        indication = Indication(code, desc, source_url,
                                                {drug_regimen}, disease)
                        all_indications[code] = indication
                    drug_regimen.indication_codes.add(indication)
    return all_regimens, all_indications


def fix_regimen_name(regimen_name, harmonization_dict=None):
    reg_name = regimen_name.lower().strip().rstrip("*")
    reg_name = re.sub(r"\xa0", r" ", reg_name)  # Replace non-breaking spaces.
    reg_name = re.sub(r" +(mono)?therapy$", r"", reg_name)  # Remove trailing 'therapy'.
    reg_name = re.sub(r"–", r"-", reg_name)  # Replace em-dash with en-dash.
    reg_name = re.sub(r" ?- ?(?=\d)", r" - ", reg_name)  # Normalize duration hyphenation.
    reg_name = re.sub(r" {2,}", r" ", reg_name)  # Remove double spacing.
    reg_name = re.sub(r"(- \d+) ?days?$", r"\1 days", reg_name)  # Normalize 'days'.
    if harmonization_dict and reg_name in harmonization_dict:
        reg_name = harmonization_dict[reg_name]
    return reg_name


def read_harmonization_file(harmonization_file):
    with open(harmonization_file) as infile:
        infile.readline()
        data = infile.readlines()
    data = [entry.split("\t") for entry in data]
    data = {entry[0]: entry[1] for entry in data}
    return data


class Indication:
    def __init__(self, code, description, source_url, regimens=None, diseases=None,
                 has_genetic_req=None, progression_flags=None):
        # From NCCP:
        self.code = code
        self.description = description
        self.source_url = source_url
        self.regimens = regimens
        if self.regimens is None:
            self.regimens = set()
        self.diseases = diseases
        if self.diseases is None:
            self.diseases = set()

        # Custom:
        self.has_genetic_req = has_genetic_req
        self.progression_flags = progression_flags

    def __repr__(self):
        string = (f"Indication(code='{self.code}', description='{self.description}', "
                  f"diseases={self.diseases})")
        return string


class Regimen:
    def __init__(self, description, indication_codes=None, diseases=None):
        self.description = description
        self.indication_codes = indication_codes
        if self.indication_codes is None:
            self.indication_codes = set()
        self.diseases = diseases
        if self.diseases is None:
            self.diseases = set()

    def __hash__(self):
        return hash(self.description)

    def __repr__(self):
        string = (f"Regimen(description='{self.description}', "
                  f"indication_codes={self.indication_codes}, "
                  f"diseases={self.diseases})")
        return string

    def merge_regimen(self, regimen):
        merged = Regimen(description=self.description,
                         indication_codes=self.indication_codes | regimen.indication_codes,
                         diseases=self.diseases | regimen.diseases)
        return merged


class NCCP_Chemotherapy_Database:
    def __init__(self, regimens, indications):
        self.regimens = regimens
        self.indications = indications

    def __str__(self):
        string = (f"NCCP_Regimen_Database:"
                  f"\n  Regimens: {len(self.regimens)}"
                  f"\n  Indications: {len(self.indications)}")
        return string

    @staticmethod
    def _validate_search_fields(searched, accepted):
        if searched is None:
            searched = accepted
        else:
            if isinstance(searched, str):
                searched = {searched}
            elif isinstance(searched, (tuple, list, set)):
                searched = set(searched)
            if not searched.issubset(accepted):
                raise ValueError(f"One or more search fields do not exist: {searched}")
        return searched

    @staticmethod
    def _search(sublist, search_text, fields):
        results = []
        for thing in sublist:
            for field in fields:
                field_value = getattr(thing, field)
                if isinstance(field_value, (list, tuple, set)):
                    field_value = ", ".join([str(x) for x in list(field_value)])
                if re.search(search_text, field_value):
                    results.append(thing)
                    break
        return results

    def search_regimens(self, search_text, fields=None):
        accepted = {"description", "diseases", "indication_codes"}
        fields = self._validate_search_fields(fields, accepted)
        results = self._search(self.regimens.values(), search_text, fields)
        return results

    def search_indications(self, search_text, fields=None):
        accepted = {"code", "description", "diseases", "regimens"}
        fields = self._validate_search_fields(fields, accepted)
        results = self._search(self.indications.values(), search_text, fields)
        return results

    def add_genetic_classification(self, genetic_indication_file):
        with open(genetic_indication_file) as infile:
            gen_inds = infile.readlines()
        gen_inds = {x.strip() for x in gen_inds}
        for indication in self.indications.values():
            indication.has_genetic_req = indication.code in gen_inds
        return

    def tabulate_indications(self):
        table = []
        for ind in self.indications.values():
            entry = [ind.code, ind.description, ", ".join(ind.diseases),
                     ", ".join([reg.description for reg in ind.regimens]),
                     ind.source_url]
            table.append(entry)
        table = pd.DataFrame(table, columns=["Code", "Indication", "Categories",
                                             "Regimen", "URL"])
        table = table.set_index("Code")
        return table


def main(harmonization_file):
    urls = get_chemoprotocol_urls()
    data = parse_tables_from_all_urls(urls)
    data = organize_parsed_tables(data, harmonization_file)
    data = NCCP_Chemotherapy_Database(*data)
    return data


if __name__ == "__main__":
    nccp_database = main("/home/tyler/Documents/Projects/PersonalizedMedicine/NCCP_Cancer_Regimens/harmonization.tsv")
