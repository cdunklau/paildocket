#!/usr/bin/env python3

import os.path
import subprocess


languages = ['de']

here = os.path.dirname(__file__)
source_dir = os.path.join(here, 'paildocket')
locale_root = os.path.join(source_dir, 'locale')
lingua_config = os.path.join(locale_root, 'lingua.conf')
pot_file = os.path.join(locale_root, 'paildocket.pot')


def create_pot_file():
    msg = 'Creating Portable Object Template (.pot) file at {0!r}'
    print(msg.format(pot_file))
    args = [
        'pot-create',
        '-c', lingua_config,
        '-o', pot_file,
        '--sort-output',
        '--copyright-holder', 'Colin Dunklau',
        '--package-name', 'Pail Docket',
        '--package-version', 'UNKNOWN',
        '--msgid-bugs-address', 'colin.dunklau@gmail.com',
        source_dir
    ]
    subprocess.check_call(args)


def initialize_po_files():
    for lang in languages:
        lang_message_dir = os.path.join(locale_root, lang, 'LC_MESSAGES')
        lang_message_file = os.path.join(lang_message_dir, 'paildocket.po')
        if not os.path.exists(lang_message_file):
            msg = 'Creating Portable Object file for language {0!r}'
            print(msg.format(lang))
            os.makedirs(lang_message_dir, exist_ok=True)
            args = [
                'msginit',
                '-l', lang,
                '-i', pot_file,
                '-o', lang_message_file
            ]
            subprocess.check_call(args)


def find_po_files():
    po_files = []
    for dirpath, dirnames, filenames in os.walk(locale_root):
        for filename in filenames:
            if filename.endswith('.po'):
                po_files.append(os.path.join(dirpath, filename))
    return po_files


def update_po_files():
    print('Updating Portable Object (.po) files')
    po_files = find_po_files()
    if not po_files:
        print('No Portable Object files found')
        return
    for po_file in po_files:
        def_file = po_file
        ref_file = pot_file
        msg = 'Merging changes in ref {0!r} to def {1!r}'
        print(msg.format(ref_file, def_file))
        args = [
            'msgmerge',
            '-v',
            '--suffix=.old',
            '--update',
            def_file,
            ref_file
        ]
        subprocess.check_call(args)


def validate_po_files():
    print('Validating Portable Object (.po) files')
    po_files = find_po_files()
    if not po_files:
        print('No Portable Object files found')
        return
    args = ['polint']
    args.extend(po_files)
    subprocess.check_call(args)


def compile_po_files():
    print(
        'Compiling Portable Object (.po) files to Message Catalog(.mo) files')
    po_files = find_po_files()
    if not po_files:
        print('No Portable Object files found')
        return
    for po_file in po_files:
        base, ext = os.path.splitext(po_file)
        mo_file = base + '.mo'
        print('Compiling {0!r} to {1!r}'.format(po_file, mo_file))
        args = ['msgfmt', '-o', mo_file, po_file]
        subprocess.check_call(args)


def main():
    print('Using locale root {0!r}'.format(locale_root))
    create_pot_file()
    initialize_po_files()
    validate_po_files()
    update_po_files()
    compile_po_files()


if __name__ == '__main__':
    main()
