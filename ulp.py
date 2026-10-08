import os
import re
import time
import io
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
WHITE = "\033[97m"

ULP_DIR = "Ulp"
RESULTS_DIR = "Results"

RE_PERSIAN = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
RE_EMAIL = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
RE_VALID_EMAIL = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
RE_SAFE_NAME = re.compile(r'[^a-zA-Z0-9._-]')

NON_COMBO_PHRASES = ('old or unknown version', 'notemmysbirthday', 'unknown version')

BUFFER_SIZE = 8 * 1024 * 1024

EDU_SUFFIXES = ('.edu', '.ac.uk', '.edu.au', '.edu.pk', '.edu.in')

FREE_DOMAINS = {
    "gmail.com", "wp.pl", "o2.pl", "interia.pl", "onet.pl",
    "yahoo.com", "outlook.com", "hotmail.com", "live.com",
    "protonmail.com", "mail.com", "aol.com", "icloud.com",
    "tlen.pl", "gazeta.pl", "poczta.fm", "op.pl", "vp.pl"
}


def is_badcombo(user, pw):
    if len(user) < 2 or len(pw) < 2:
        return True
    if pw.strip() == "":
        return True
    for c in user:
        if c in ' \t\r\n':
            return True
    for c in pw:
        if c in ' \t\r\n':
            return True
    ul, pl = user.lower(), pw.lower()
    for phrase in NON_COMBO_PHRASES:
        if phrase in ul or phrase in pl:
            return True
    if RE_PERSIAN.search(user) or RE_PERSIAN.search(pw):
        return True
    return False


def logo():
    print(f"""{BLUE}{BOLD}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⠻⣆⠀⠀⠀⠘⠀⠐⠀⠀⠀⡀⠀
⠀⠀⡶⢤⡀⠀⠀⠀⢀⡇⡄⠈⢳⡄⢀⠁⠀⠀⠀⠀⠀⠇⠀
⠀⢠⡇⡄⢙⢦⣀⣀⣼⠁⠂⠀⠀⠙⣦⠀⠀⠀⠀⠀⠠⠀⠀
⠀⠘⡇⡇⠀⠁⡍⠁⠀⠀⠈⡁⠂⠀⢌⠳⡄⠀⠀⠀⠐⠀⠀
⠀⠰⡇⢀⠀⡐⠁⠀⠀⠀⠀⠀⢀⡴⣋⡄⠹⣆⠀⢠⠀⠀⠀
⠀⠀⣗⠈⢅⣀⣀⣀⡀⠀⠀⠀⠛⠛⠤⠤⠤⡸⣆⣠⠟⢲⡄
⠀⠀⣿⠀⠰⠒⣺⠟⠁⢀⣠⠤⠶⡄⡁⠀⢀⠆⢹⠁⣠⠞⠁
⠀⠀⢻⡀⢀⠞⠑⠒⢄⢣⡀⠀⠀⡇⠈⠉⠀⣠⣾⡜⠃⠀⠀
⢀⣤⣼⣇⠈⠠⠤⠄⠊⠀⠑⠤⢠⣃⣠⠴⢛⡿⠋⠀⠀⠀⠀
⠸⢤⣄⣈⡓⡦⠤⠤⠤⠴⠖⠚⠋⠉⠀⢸⡍⠄⠀⠀⠀⠀⠀
⠀⠀⠀⠈⠉⠉⠛⠛⠒⢷⠀⠀⠀⠀⠀⠀⢷⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⢘⡃⠀⠀⠀⠀⠀⠘⡃⠀⠀⠀⠀⠀
               {WHITE}O w n e r  ~ @ u p d h 2{BLUE}
{RESET}""")


def parse_ulp(line):
    idx = line.rfind(':')
    if idx == -1:
        return None, 'BAD'
    idx2 = line.rfind(':', 0, idx)
    if idx2 == -1:
        user = line[:idx]
    else:
        user = line[idx2 + 1:idx]
    pw = line[idx + 1:]
    user = user.strip()
    pw = pw.strip()
    if is_badcombo(user, pw):
        return None, 'BAD'
    return f"{user}:{pw}", 'OK'


def sizeof_fmt(num, suffix="B"):
    for unit in ['', 'K', 'M', 'G', 'T', 'P']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Y', suffix)


def print_dashboard(stat):
    print(f"\n{CYAN}{'='*56}{RESET}")
    print(f"{CYAN}{WHITE}{'Extraction Summary':^56}{CYAN}{RESET}")
    print(f"{CYAN}{'='*56}{RESET}")
    print(f"{YELLOW}Target        {RESET}: {stat['target']}")
    print(f"{YELLOW}Files Scanned {RESET}: {stat['files_scanned']}")
    print(f"{YELLOW}Total Lines   {RESET}: {stat['total_lines']:,}")
    print(f"{GREEN}Output File   {RESET}: {stat['outfile']}")
    print(f"{GREEN}Output Size   {RESET}: {stat['outfile_size']}")
    print(f"{BLUE}Unique        {RESET}: {stat['unique_combos']:,}")
    print(f"{MAGENTA}Duplicates    {RESET}: {stat['duplicates']:,}")
    print(f"{RED}Bad Chars     {RESET}: {stat['bad_charcount']:,}")
    print(f"{CYAN}Time          {RESET}: {stat['elapsed']:.2f} s")
    print(f"{CYAN}Speed         {RESET}: {stat['speed']:,} l/s")


def get_txt_files():
    if not os.path.isdir(ULP_DIR):
        print(RED + f"Folder '{ULP_DIR}' does not exist!" + RESET)
        return []
    files = [f for f in os.listdir(ULP_DIR) if f.lower().endswith('.txt')]
    if not files:
        print(RED + f"No .txt files found in '{ULP_DIR}' folder!" + RESET)
        return []
    return files


def ensure_results_dir():
    if not os.path.isdir(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)


def write_shuffled(outfile, items):
    items = list(items)
    random.shuffle(items)
    with io.open(outfile, "w", encoding="utf-8", buffering=BUFFER_SIZE) as fout:
        fout.write('\n'.join(items))
        if items:
            fout.write('\n')


def _process_combo_file(path, target):
    local_unique = set()
    local_valid = 0
    local_dup = 0
    local_bad = 0
    local_lines = 0

    target_l = target.lower() if target else None

    with io.open(path, "r", encoding="utf-8", errors="ignore", buffering=BUFFER_SIZE) as f:
        for raw_line in f:
            local_lines += 1
            if ':' not in raw_line:
                local_bad += len(raw_line)
                continue
            if target_l and target_l not in raw_line.lower():
                continue
            raw = raw_line.strip()
            if not raw:
                continue
            result, status = parse_ulp(raw)
            if status == 'OK':
                local_valid += 1
                if result in local_unique:
                    local_dup += 1
                else:
                    local_unique.add(result)
            else:
                local_bad += len(raw)

    return {
        'lines': local_lines,
        'unique': local_unique,
        'valid': local_valid,
        'dup': local_dup,
        'bad': local_bad
    }


def _process_emailpass_file(path, mode, target=None):
    local_unique = set()
    local_lines = 0
    local_bad = 0

    target_l = target.lower() if target else None
    parse = parse_ulp

    with io.open(path, "r", encoding="utf-8", errors="ignore", buffering=BUFFER_SIZE) as f:
        for raw_line in f:
            local_lines += 1
            if ':' not in raw_line or '@' not in raw_line:
                local_bad += len(raw_line)
                continue
            if target_l and target_l not in raw_line.lower():
                continue
            raw = raw_line.strip()
            if not raw:
                continue

            combo, status = parse(raw)
            if status != 'OK':
                local_bad += len(raw)
                continue

            email = combo.split(':', 1)[0]
            if not RE_VALID_EMAIL.match(email):
                continue

            domain = email.split('@', 1)[1].lower()

            if mode == 'edu':
                if domain.endswith(EDU_SUFFIXES) or '.edu.' in domain:
                    local_unique.add(combo)
            elif mode == 'corp':
                if domain not in FREE_DOMAINS:
                    local_unique.add(combo)

    return local_unique, local_lines, local_bad


def _process_leads_file(path, target):
    local_unique = set()
    local_lines = 0

    target_l = target.lower() if target else None
    email_findall = RE_EMAIL.findall
    valid_match = RE_VALID_EMAIL.match

    with io.open(path, "r", encoding="utf-8", errors="ignore", buffering=BUFFER_SIZE) as f:
        for raw_line in f:
            local_lines += 1
            if '@' not in raw_line:
                continue
            if target_l and target_l not in raw_line.lower():
                continue

            emails = email_findall(raw_line)
            if not emails:
                continue

            for email in emails:
                if not valid_match(email):
                    continue
                local_unique.add(email.lower())

    return local_unique, local_lines


def _run_parallel(files, worker, max_workers=None):
    if max_workers is None:
        max_workers = min(8, (os.cpu_count() or 4) * 2)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(worker, os.path.join(ULP_DIR, name)): name for name in files}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                yield name, fut.result()
            except Exception as e:
                yield name, e


def extract_ulp_combo():
    txt_files = get_txt_files()
    if not txt_files:
        return

    target = input(YELLOW + "\nEnter target (e.g. netflix, .ir, spotify): " + RESET).strip()
    if not target:
        print(RED + "Target cannot be empty!" + RESET)
        return

    print(GREEN + f"Searching for: {target} across {len(txt_files)} file(s)..." + RESET)

    ensure_results_dir()
    outfile = os.path.join(RESULTS_DIR, "converted_combo.txt")

    t0 = time.time()

    all_unique = set()
    total_lines = 0
    total_valid = 0
    total_dup = 0
    total_bad = 0
    done = 0

    for name, result in _run_parallel(txt_files, lambda p: _process_combo_file(p, target)):
        if isinstance(result, Exception):
            print(RED + f"Error on {name}: {result}" + RESET)
            continue
        done += 1
        total_lines += result['lines']
        total_valid += result['valid']
        total_dup += result['dup']
        total_bad += result['bad']
        for item in result['unique']:
            if item in all_unique:
                total_dup += 1
            else:
                all_unique.add(item)
        print(f"{CYAN}  [{done}/{len(txt_files)}] {name}: total {len(all_unique)} unique{RESET}", end='\r')

    print()

    write_shuffled(outfile, all_unique)

    t1 = time.time()
    outfile_size = sizeof_fmt(os.path.getsize(outfile))
    avg_speed = int(total_lines / (t1 - t0)) if (t1 - t0) > 0 else total_lines

    stat = {
        'target': target,
        'files_scanned': len(txt_files),
        'total_lines': total_lines,
        'outfile': outfile,
        'outfile_size': outfile_size,
        'unique_combos': len(all_unique),
        'duplicates': total_dup,
        'bad_charcount': total_bad,
        'elapsed': t1 - t0,
        'speed': avg_speed
    }
    print_dashboard(stat)


def extract_corp_mails():
    txt_files = get_txt_files()
    if not txt_files:
        return

    print(GREEN + "Extracting corporate email:pass combos..." + RESET)
    ensure_results_dir()
    outfile = os.path.join(RESULTS_DIR, "Corp_Data.txt")

    t0 = time.time()
    all_unique = set()
    total_lines = 0
    total_bad = 0
    done = 0

    for name, result in _run_parallel(txt_files, lambda p: _process_emailpass_file(p, 'corp')):
        if isinstance(result, Exception):
            print(RED + f"Error on {name}: {result}" + RESET)
            continue
        done += 1
        emails, lines, bad = result
        total_lines += lines
        total_bad += bad
        all_unique |= emails
        print(f"{CYAN}  [{done}/{len(txt_files)}] {name}: total {len(all_unique)} unique{RESET}", end='\r')

    print()

    write_shuffled(outfile, all_unique)

    t1 = time.time()
    outfile_size = sizeof_fmt(os.path.getsize(outfile))
    avg_speed = int(total_lines / (t1 - t0)) if (t1 - t0) > 0 else total_lines

    stat = {
        'target': 'Corporate email:pass',
        'files_scanned': len(txt_files),
        'total_lines': total_lines,
        'outfile': outfile,
        'outfile_size': outfile_size,
        'unique_combos': len(all_unique),
        'duplicates': 0,
        'bad_charcount': total_bad,
        'elapsed': t1 - t0,
        'speed': avg_speed
    }
    print_dashboard(stat)


def extract_edu_mails():
    txt_files = get_txt_files()
    if not txt_files:
        return

    print(GREEN + "Extracting educational email:pass combos..." + RESET)
    ensure_results_dir()
    outfile = os.path.join(RESULTS_DIR, "Edu_Data.txt")

    t0 = time.time()
    all_unique = set()
    total_lines = 0
    total_bad = 0
    done = 0

    for name, result in _run_parallel(txt_files, lambda p: _process_emailpass_file(p, 'edu')):
        if isinstance(result, Exception):
            print(RED + f"Error on {name}: {result}" + RESET)
            continue
        done += 1
        emails, lines, bad = result
        total_lines += lines
        total_bad += bad
        all_unique |= emails
        print(f"{CYAN}  [{done}/{len(txt_files)}] {name}: total {len(all_unique)} unique{RESET}", end='\r')

    print()

    write_shuffled(outfile, all_unique)

    t1 = time.time()
    outfile_size = sizeof_fmt(os.path.getsize(outfile))
    avg_speed = int(total_lines / (t1 - t0)) if (t1 - t0) > 0 else total_lines

    stat = {
        'target': 'Educational email:pass',
        'files_scanned': len(txt_files),
        'total_lines': total_lines,
        'outfile': outfile,
        'outfile_size': outfile_size,
        'unique_combos': len(all_unique),
        'duplicates': 0,
        'bad_charcount': total_bad,
        'elapsed': t1 - t0,
        'speed': avg_speed
    }
    print_dashboard(stat)


def extract_leads():
    txt_files = get_txt_files()
    if not txt_files:
        return

    target = input(YELLOW + "\nEnter target (e.g. netflix, spotify, .ir): " + RESET).strip()
    if not target:
        print(RED + "Target cannot be empty!" + RESET)
        return

    print(GREEN + f"Extracting emails matching '{target}'..." + RESET)
    ensure_results_dir()
    safe_target = RE_SAFE_NAME.sub('_', target)
    outfile = os.path.join(RESULTS_DIR, f"Leads_{safe_target}.txt")

    t0 = time.time()
    all_unique = set()
    total_lines = 0
    done = 0

    for name, result in _run_parallel(txt_files, lambda p: _process_leads_file(p, target)):
        if isinstance(result, Exception):
            print(RED + f"Error on {name}: {result}" + RESET)
            continue
        done += 1
        emails, lines = result
        total_lines += lines
        all_unique |= emails
        print(f"{CYAN}  [{done}/{len(txt_files)}] {name}: total {len(all_unique)} unique{RESET}", end='\r')

    print()

    write_shuffled(outfile, all_unique)

    t1 = time.time()
    outfile_size = sizeof_fmt(os.path.getsize(outfile))
    avg_speed = int(total_lines / (t1 - t0)) if (t1 - t0) > 0 else total_lines

    stat = {
        'target': f'Leads ({target})',
        'files_scanned': len(txt_files),
        'total_lines': total_lines,
        'outfile': outfile,
        'outfile_size': outfile_size,
        'unique_combos': len(all_unique),
        'duplicates': 0,
        'bad_charcount': 0,
        'elapsed': t1 - t0,
        'speed': avg_speed
    }
    print_dashboard(stat)


def main_menu():
    while True:
        logo()
        print(f"{CYAN}{WHITE}{'MAIN MENU':^42}{CYAN}{RESET}")
        print(f"{CYAN}{RESET}  {GREEN}[1]{RESET} Extract ULP -> Combo")
        print(f"{CYAN}{RESET}  {GREEN}[2]{RESET} Extract Corp Mails")
        print(f"{CYAN}{RESET}  {GREEN}[3]{RESET} Extract Edu Mails")
        print(f"{CYAN}{RESET}  {GREEN}[4]{RESET} Extract Leads")
        print(f"{CYAN}{RESET}  {RED}[5]{RESET} Exit")

        choice = input(YELLOW + "\nSelect option [1-5]: " + RESET).strip()

        if choice == '1':
            extract_ulp_combo()
            input(YELLOW + "\nPress Enter to return to menu..." + RESET)
        elif choice == '2':
            extract_corp_mails()
            input(YELLOW + "\nPress Enter to return to menu..." + RESET)
        elif choice == '3':
            extract_edu_mails()
            input(YELLOW + "\nPress Enter to return to menu..." + RESET)
        elif choice == '4':
            extract_leads()
            input(YELLOW + "\nPress Enter to return to menu..." + RESET)
        elif choice == '5':
            print(GREEN + "Goodbye!" + RESET)
            break
        else:
            print(RED + "Invalid option! Try again." + RESET)
            time.sleep(1)


def main():
    main_menu()


if __name__ == "__main__":
    main()
