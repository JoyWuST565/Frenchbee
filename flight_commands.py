"""Offline command syntax and country code lookup; no database or GUI effects."""

from __future__ import annotations

import re
import shlex


# ISO 3166 alpha-2 codes, checked against Unicode CLDR territories (2026-09-10).
# Names retain the application's existing English dropdown spelling.
COUNTRY_NAMES = {
    "AF": "Afghanistan", "AL": "Albania", "DZ": "Algeria", "AD": "Andorra",
    "AO": "Angola", "AG": "Antigua and Barbuda", "AR": "Argentina", "AM": "Armenia",
    "AU": "Australia", "AT": "Austria", "AZ": "Azerbaijan", "BS": "Bahamas",
    "BH": "Bahrain", "BD": "Bangladesh", "BB": "Barbados", "BY": "Belarus",
    "BE": "Belgium", "BZ": "Belize", "BJ": "Benin", "BT": "Bhutan",
    "BO": "Bolivia", "BA": "Bosnia and Herzegovina", "BW": "Botswana", "BR": "Brazil",
    "BN": "Brunei", "BG": "Bulgaria", "BF": "Burkina Faso", "BI": "Burundi",
    "CV": "Cabo Verde", "KH": "Cambodia", "CM": "Cameroon", "CA": "Canada",
    "CF": "Central African Republic", "TD": "Chad", "CL": "Chile", "CN": "China",
    "CO": "Colombia", "KM": "Comoros", "CG": "Congo", "CR": "Costa Rica",
    "CI": "Cote d'Ivoire", "HR": "Croatia", "CU": "Cuba", "CY": "Cyprus",
    "CZ": "Czechia", "DK": "Denmark", "DJ": "Djibouti", "DM": "Dominica",
    "DO": "Dominican Republic", "CD": "DR Congo", "EC": "Ecuador", "EG": "Egypt",
    "SV": "El Salvador", "GQ": "Equatorial Guinea", "ER": "Eritrea", "EE": "Estonia",
    "SZ": "Eswatini", "ET": "Ethiopia", "FJ": "Fiji", "FI": "Finland",
    "FR": "France", "GA": "Gabon", "GM": "Gambia", "GE": "Georgia",
    "DE": "Germany", "GH": "Ghana", "GR": "Greece", "GD": "Grenada",
    "GT": "Guatemala", "GN": "Guinea", "GW": "Guinea-Bissau", "GY": "Guyana",
    "HT": "Haiti", "VA": "Holy See", "HN": "Honduras", "HU": "Hungary",
    "IS": "Iceland", "IN": "India", "ID": "Indonesia", "IR": "Iran",
    "IQ": "Iraq", "IE": "Ireland", "IL": "Israel", "IT": "Italy",
    "JM": "Jamaica", "JP": "Japan", "JO": "Jordan", "KZ": "Kazakhstan",
    "KE": "Kenya", "KI": "Kiribati", "KW": "Kuwait", "KG": "Kyrgyzstan",
    "LA": "Laos", "LV": "Latvia", "LB": "Lebanon", "LS": "Lesotho",
    "LR": "Liberia", "LY": "Libya", "LI": "Liechtenstein", "LT": "Lithuania",
    "LU": "Luxembourg", "MG": "Madagascar", "MW": "Malawi", "MY": "Malaysia",
    "MV": "Maldives", "ML": "Mali", "MT": "Malta", "MH": "Marshall Islands",
    "MR": "Mauritania", "MU": "Mauritius", "MX": "Mexico", "FM": "Micronesia",
    "MD": "Moldova", "MC": "Monaco", "MN": "Mongolia", "ME": "Montenegro",
    "MA": "Morocco", "MZ": "Mozambique", "MM": "Myanmar", "NA": "Namibia",
    "NR": "Nauru", "NP": "Nepal", "NL": "Netherlands", "NZ": "New Zealand",
    "NI": "Nicaragua", "NE": "Niger", "NG": "Nigeria", "KP": "North Korea",
    "MK": "North Macedonia", "NO": "Norway", "OM": "Oman", "PK": "Pakistan",
    "PW": "Palau", "PS": "Palestine", "PA": "Panama", "PG": "Papua New Guinea",
    "PY": "Paraguay", "PE": "Peru", "PH": "Philippines", "PL": "Poland",
    "PT": "Portugal", "QA": "Qatar", "RO": "Romania", "RU": "Russia",
    "RW": "Rwanda", "KN": "Saint Kitts and Nevis", "LC": "Saint Lucia",
    "VC": "Saint Vincent and the Grenadines", "WS": "Samoa", "SM": "San Marino",
    "ST": "Sao Tome and Principe", "SA": "Saudi Arabia", "SN": "Senegal", "RS": "Serbia",
    "SC": "Seychelles", "SL": "Sierra Leone", "SG": "Singapore", "SK": "Slovakia",
    "SI": "Slovenia", "SB": "Solomon Islands", "SO": "Somalia", "ZA": "South Africa",
    "KR": "South Korea", "SS": "South Sudan", "ES": "Spain", "LK": "Sri Lanka",
    "SD": "Sudan", "SR": "Suriname", "SE": "Sweden", "CH": "Switzerland",
    "SY": "Syria", "TJ": "Tajikistan", "TZ": "Tanzania", "TH": "Thailand",
    "TL": "Timor-Leste", "TG": "Togo", "TO": "Tonga", "TT": "Trinidad and Tobago",
    "TN": "Tunisia", "TR": "Turkiye", "TM": "Turkmenistan", "TV": "Tuvalu",
    "AE": "UAE", "UG": "Uganda", "UA": "Ukraine", "GB": "UK", "UY": "Uruguay",
    "US": "USA", "UZ": "Uzbekistan", "VU": "Vanuatu", "VE": "Venezuela",
    "VN": "Vietnam", "YE": "Yemen", "ZM": "Zambia", "ZW": "Zimbabwe",
    "HK": "Hong Kong SAR China", "MO": "Macao SAR China", "TW": "Taiwan",
    "RE": "Reunion", "PF": "French Polynesia", "NC": "New Caledonia", "SX": "Sint Maarten",
    "GF": "French Guiana", "GP": "Guadeloupe", "MQ": "Martinique", "YT": "Mayotte",
}
COUNTRY_ALIASES = {
    "United States": "US", "United States of America": "US", "United Kingdom": "GB",
    "United Arab Emirates": "AE", "Vatican City": "VA", "Cape Verde": "CV",
    "Hong Kong": "HK", "Macao": "MO", "Macau": "MO", "Turkey": "TR",
    "Czech Republic": "CZ", "Democratic Republic of the Congo": "CD",
    "Republic of the Congo": "CG", "Congo - Kinshasa": "CD", "Congo - Brazzaville": "CG",
}
NAME_TO_CODE = {name.casefold(): code for code, name in COUNTRY_NAMES.items()}
NAME_TO_CODE.update({name.casefold(): code for name, code in COUNTRY_ALIASES.items()})


def default_country_code(name: str) -> str:
    return NAME_TO_CODE.get(name.strip().casefold(), "")


def expand_flight_numbers(token: str) -> tuple[str, str, str]:
    match = re.fullmatch(r"([A-Z0-9]{2})([0-9]{1,4})/([A-Z0-9]+)", token.upper())
    if not match:
        raise ValueError("往返航班号格式有误，例如 9C1234/5 或 9C1239/40。")
    code, outbound, suffix = match.groups()
    if re.fullmatch(r"[0-9]{1,4}", suffix):
        inbound = outbound[:-len(suffix)] + suffix if len(suffix) < len(outbound) else suffix
        inbound = code + inbound
    elif re.fullmatch(re.escape(code) + r"[0-9]{1,4}", suffix):
        inbound = suffix
    else:
        raise ValueError("返程航班号必须是 1–4 位数字简写，或带相同二字代码的完整航班号。")
    return code, code + outbound, inbound


def match_option(names: list[str], value: str, label: str) -> str:
    matches = [name for name in names if name.casefold() == value.casefold()]
    if len(matches) != 1:
        raise ValueError(f"{label}“{value}”未在当前母公司的列表中唯一匹配，请管理该选项或手动选择。")
    return matches[0]


def parse_command_fields(line: str, options: dict) -> tuple[dict[str, str], list[str]]:
    record: dict[str, str] = {}
    errors: list[str] = []
    try:
        tokens = shlex.split(line)
    except ValueError as exc:
        return record, [f"命令引号不完整：{exc}"]
    if len(tokens) != 5:
        return record, ["命令必须按顺序包含 5 组数据：航线 往返航班号 起降时间 机型-班期 国家/地区代码。"]
    route, flights, times, equipment, country = tokens
    match = re.fullmatch(r"([A-Z]{3})-([A-Z]{3})", route.upper())
    if match:
        record["departure_airport_code"], record["airport_code"] = match.groups()
    else:
        errors.append("航线格式应为 PVG-CAN，两个机场代码均须为三位英文字母。")
    try:
        code, record["outbound_flight_no"], record["return_flight_no"] = expand_flight_numbers(flights)
        names = [name for name in options.get("airlines", []) if options.get("airline_codes", {}).get(name, "").upper() == code]
        if len(names) != 1:
            raise ValueError(f"子公司代码 {code} 对应 {len(names)} 家子公司，请管理二字代码或手动选择子公司。")
        record["airline"] = names[0]
    except ValueError as exc:
        errors.append(str(exc))
    match = re.fullmatch(r"([0-9]{4})/([0-9]{4})", times)
    if match:
        for field, time in zip(("departure_time", "arrival_time"), match.groups()):
            if int(time[:2]) > 23 or int(time[2:]) > 59:
                errors.append(f"时间 {time} 无效，必须介于 0000 和 2359。")
            elif int(time[2:]) % 5:
                errors.append(f"时间 {time} 必须使用每 5 分钟一个间隔的分钟值。")
            else:
                record[field] = time[:2] + ":" + time[2:]
    else:
        errors.append("起降时间格式应为四位数字/四位数字，例如 1230/1900。")
    aircraft, sep, frequency = equipment.rpartition("-")
    if not sep or not aircraft:
        errors.append("机型及班期格式应为 A339-7。")
    else:
        record["weekly_frequency"] = frequency
        try:
            record["aircraft_type"] = match_option(options.get("aircraft_types", []), aircraft, "机型")
        except ValueError as exc:
            errors.append(str(exc))
    country = country.upper()
    try:
        names = options.get("countries_or_regions", [])
        if country == "D":
            domestic = options.get("domestic_country", "")
            record["country_or_region"] = match_option(names, domestic, "国内国家/地区（D）")
        elif re.fullmatch(r"[A-Z]{2}", country):
            codes = options.get("country_codes", {})
            matches = [name for name in names if codes.get(name, default_country_code(name)).upper() == country]
            if len(matches) != 1:
                raise ValueError(f"国家/地区代码 {country} 对应 {len(matches)} 项，请在国家/地区管理中设置代码或手动选择。")
            record["country_or_region"] = matches[0]
        else:
            raise ValueError("国家/地区必须为 D 或两位英文字母代码，例如 US、FR。")
    except ValueError as exc:
        errors.append(str(exc))
    return record, errors


def missing_command_options(text: str, options: dict) -> list[tuple[str, str, str]]:
    """Return unique missing (field, command token, suggested name) registrations."""
    missing: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        try:
            tokens = shlex.split(line)
        except ValueError:
            continue
        if len(tokens) != 5:
            continue
        try:
            code, _, _ = expand_flight_numbers(tokens[1])
            if not any(options.get("airline_codes", {}).get(name, "").upper() == code for name in options.get("airlines", [])):
                missing.append(("airline", code, ""))
        except ValueError:
            pass
        aircraft, sep, _ = tokens[3].rpartition("-")
        if sep and aircraft and not any(name.casefold() == aircraft.casefold() for name in options.get("aircraft_types", [])):
            missing.append(("aircraft_type", aircraft, aircraft))
        country = tokens[4].upper()
        names = options.get("countries_or_regions", [])
        if country == "D":
            if not options.get("domestic_country") or options["domestic_country"] not in names:
                missing.append(("country_or_region", "D", ""))
        elif re.fullmatch(r"[A-Z]{2}", country):
            codes = options.get("country_codes", {})
            if not any(codes.get(name, default_country_code(name)).upper() == country for name in names):
                missing.append(("country_or_region", country, COUNTRY_NAMES.get(country, "")))
    return list(dict.fromkeys(missing))
