"""Level 1: the functions of the script, called directly with tables of cases.

The references in the comments (SF-x, L-x, §) point to SPECIFICATIONS.md.
"""

H = 'ABCDEF1234567890ABCDEF1234567890'          # a valid MD4 hash: 32 hexadecimal characters


def test_isEd2kLink(t):
    """SF-1.3: the ed2k scheme, literal or encoded at any depth; nothing else."""
    t.load()
    cases = [
        (f'ed2k://|file|a.mp3|1|{H}|/', True),
        (f'ED2K://|file|a.mp3|1|{H}|/', True),                      # case-insensitive
        ('ed2k%3A%2F%2F%7Cfile%7Ca.mp3', True),                     # encoded scheme (SF-1.3)
        ('ed2k%253A%252F%252F%257Cfile%257Ca.mp3', True),           # scheme encoded twice
        ('ed2k-guide.html', False),                                 # relative link (SF-1 note)
        ('ed2klinks/page1', False),
        ('ed2:something', False),                                   # the old regex accepted it
        ('https://example.com/', False),
    ]
    for href, expected in cases:
        t.eq(t.call('isEd2kLink', href), expected, f'isEd2kLink({href!r})')


def test_decodeEd2kLink(t):
    """SF-1.4: decoded in passes until the scheme is readable."""
    t.load()
    plain = f'ed2k://|file|a.mp3|1|{H}|/'
    cases = [
        (plain, plain),
        (f'ed2k://%7Cfile%7Ca.mp3%7C1%7C{H}%7C%2F', plain),
        (f'ed2k%3A%2F%2F%7Cfile%7Ca.mp3%7C1%7C{H}%7C%2F', plain),
        (f'ed2k%253A%252F%252F%257Cfile%257Ca.mp3%257C1%257C{H}%257C%252F', plain),
        (f'ed2k://|file|Conf%C3%A9rence.mkv|1|{H}|/', f'ed2k://|file|Conférence.mkv|1|{H}|/'),
        # a name encoded twice keeps one level: SF-1.8 decodes it later, on the name only
        (f'ed2k://|file|Fran%25C3%25A7ois.docx|1|{H}|/', f'ed2k://|file|Fran%C3%A7ois.docx|1|{H}|/'),
        # invalid UTF-8 (legacy ISO-Latin encoding): unescape() fallback
        (f'ed2k://|file|%E0.zip|1|{H}|/', f'ed2k://|file|à.zip|1|{H}|/'),
    ]
    for href, expected in cases:
        t.eq(t.call('decodeEd2kLink', href), expected, f'decodeEd2kLink({href!r})')


def test_isValidEd2kFile(t):
    """SF-1.7: structural validation of a split link."""
    t.load()
    cases = [
        (f'ed2k://|file|a.mp3|1048576|{H}|/', True),
        (f'ed2k://|FILE|a.mp3|1048576|{H}|/', True),
        (f'ed2k://|file|a.mp3|1048576|{H}|h=YNCKHTQCWBTRHHQTGPWDQPGBIZJREOB5|/', True),
        ('ed2k://xxxxxxxx', False),                                 # malformed
        ('ed2k://|server|192.168.1.1|4661|/', False),               # not a file
        ('ed2k://|serverlist|http://example.com/server.met|/', False),
        (f'ed2k://|file||1048576|{H}|/', False),                    # empty name
        (f'ed2k://|file|a.mp3|abc|{H}|/', False),                   # size not numeric
    ]
    for link, expected in cases:
        t.eq(t.call('isValidEd2kFile', link.split('|')), expected, f'isValidEd2kFile({link!r})')


def test_encodeEd2kLink(t):
    """SF-7.7: the part between ed2k:// and the final / is percent-encoded."""
    t.load()
    cases = [
        (f'ed2k://|file|a b.mp3|1|{H}|/', f'ed2k://%7Cfile%7Ca%20b.mp3%7C1%7C{H}%7C/'),
        (f'ed2k://|file|Été (Café).mp3|1|{H}|/',
         f'ed2k://%7Cfile%7C%C3%89t%C3%A9%20(Caf%C3%A9).mp3%7C1%7C{H}%7C/'),
        (f'ed2k://|file|[R]#1?.txt|1|{H}|/', f'ed2k://%7Cfile%7C%5BR%5D%231%3F.txt%7C1%7C{H}%7C/'),
        (f'ed2k://|file|a.mp3|1|{H}|h=ABC|/', f'ed2k://%7Cfile%7Ca.mp3%7C1%7C{H}%7Ch%3DABC%7C/'),
        # a literal % that is not an escape sequence: encoded as is
        (f'ed2k://|file|100%.txt|1|{H}|/', f'ed2k://%7Cfile%7C100%25.txt%7C1%7C{H}%7C/'),
        ('https://example.com/', 'https://example.com/'),            # not ed2k: unchanged
    ]
    for link, expected in cases:
        encoded = t.call('encodeEd2kLink', link)
        t.eq(encoded, expected, f'encodeEd2kLink({link!r})')
        t.eq(t.call('encodeEd2kLink', encoded), encoded, f'encoding {link!r} twice changes nothing')


def test_strToCat(t):
    """SF-6.5 and SF-6.7: invalid entries skipped, exactly one default; the value is everything after
    the first = (an aMule 2.x category named A=B), a ; written \\; in a name or a value (test;23)."""
    t.load()

    def cats(*entries):
        return [{'name': n, 'value': v, 'select': s} for n, v, s in entries]

    cases = [
        ('', -1),                                                   # used to crash the script
        (';;;', -1),
        ('=0', -1),
        ('*default=0;', cats(('default', '0', 1))),
        ('*Audio=1;Video', cats(('Audio', '1', 1))),                # Video has no value
        ('Audio=1;Video=2', cats(('Audio', '1', 1), ('Video', '2', 0))),       # no *
        ('*Audio=1;*Video=2', cats(('Audio', '1', 1), ('Video', '2', 0))),     # two *
        ('BD=BD;*Manga=Manga', cats(('BD', 'BD', 0), ('Manga', 'Manga', 1))),
        ('*Audio = 1 ; Video = 2', cats(('Audio', '1', 1), ('Video', '2', 0))),  # spaces
        ('A B=A=B;*all=all', cats(('A B', 'A=B', 0), ('all', 'all', 1))),        # = in the value
        ('test 23=test\\;23;*all=all', cats(('test 23', 'test;23', 0), ('all', 'all', 1))),  # \; in the value
        ('*a\\;b=1', cats(('a;b', '1', 1))),                                     # \; in the name
    ]
    for text, expected in cases:
        t.eq(t.call('strToCat', text), expected, f'strToCat({text!r})')


def test_catToStr(t):
    """Categories back to the settings text, a ; written \\;, and the round trip."""
    t.load()
    categories = [{'name': 'Audio', 'value': '1', 'select': 1},
                  {'name': 'Video', 'value': '2', 'select': 0},
                  {'name': 'test 23', 'value': 'test;23', 'select': 0}]
    text = t.call('catToStr', categories)
    t.eq(text, '*Audio=1;Video=2;test 23=test\\;23;', 'catToStr')
    t.eq(t.call('strToCat', text), categories, 'strToCat(catToStr(x)) == x')


def test_amuleWebCategory(t):
    """SF-7.13: the category of aMule 2.x, encoded as amuleweb 2.3.3 reads it (its UTF-8 bytes taken
    as characters): unchanged without accents."""
    t.load()
    for name, expected in (('BD', 'BD'), ('all', 'all'), ('Vidéo & Co', 'Vid%C3%83%C2%A9o%20%26%20Co'),
                           ('2ème Catégorie', '2%C3%83%C2%A8me%20Cat%C3%83%C2%A9gorie')):
        t.eq(t.call('amuleWebCategory', name), expected, f'amuleWebCategory({name!r})')


def test_mergeCategories(t):
    """SF-8.18: the categories of the client (aMule, eMule) in its order, the category 0 under its own name, the
    default one kept by its name (whatever the case) or else the first one, the names cleaned
    of the syntax of the field; Default=0 when aMule has none."""
    t.load()

    def cats(*names):
        return [{'index': i, 'name': n} for i, n in enumerate(names)]

    cases = [
        (cats('Default', 'Audio', 'Video', 'Documents', 'Software'), '*Video=2;Audio=1;Documents=3',
         'Default=0;Audio=1;*Video=2;Documents=3;Software=4',
         '5 categories imported from aMule: 2 new (Default, Software). Video stays the default (*).'),
        # the category 0 renamed in aMule, the default one gone: the first one becomes the default
        (cats('Tout', 'Audio', 'Films'), '*Video=2;Audio=1', '*Tout=0;Audio=1;Films=2',
         '3 categories imported from aMule: 2 new (Tout, Films), 1 removed (Video). Tout is now the default (*).'),
        ([], '*Video=2', '*Default=0', 'aMule has no category: Default=0 is used.'),
        (cats('Default', 'Video'), '*video=2;default=0', 'Default=0;*Video=1',
         '2 categories imported from aMule. Video stays the default (*).'),       # any case; moved index
        (cats('Default', 'Audio'), 'Audio=1;Default=0', 'Default=0;*Audio=1',      # no *: the first one
         '2 categories imported from aMule. Audio stays the default (*).'),        # was the default (SF-6.7)
        (cats('Default', 'A;B', 'x=y', '*Star', '  '), '', '*Default=0;A B=1;x y=2;Star=3;Category 4=4',
         None),                                                                   # syntax taken out
        (cats('Default', 'A', 'B', 'C', 'D'), 'garbage', '*Default=0;A=1;B=2;C=3;D=4',
         '5 categories imported from aMule: 5 new (Default, A, B, …). Default is now the default (*).'),
        ([{'index': 3, 'name': 'Video'}, {'index': 1, 'name': 'Audio'}], '*Audio=1', 'Video=3;*Audio=1',
         None),                                                                   # the order of aMule
    ]
    # eMule: its category 0 is named All; an accent; the client named in the message
    merged = t.call('mergeCategories', cats('All', 'BD', 'Testé'), '*default=0;BD=1', 'eMule')
    t.eq(merged, {'value': '*All=0;BD=1;Testé=2',
                  'message': '3 categories imported from eMule: 2 new (All, Testé), 1 removed (default). All is now the default (*).'},
         'eMule: All=0, the accent kept, eMule named')
    # aMule 2.x: the categories known by their name, the value being the name: an = kept in it, a ;
    # written \\; (the separator of the field); the name shown without them
    merged = t.call('mergeCategories', [{'index': n, 'name': n} for n in ('all', 'Vidéo', 'A;B', 'A=B')], '*Vidéo=Vidéo',
                    'aMule', True)
    t.eq(merged['value'], 'all=all;*Vidéo=Vidéo;A B=A\\;B;A B=A=B', 'aMule 2.x: name=name, the default kept')
    for categories, current, value, message in cases:
        merged = t.call('mergeCategories', categories, current)
        t.eq(merged['value'], value, f'mergeCategories({[c["name"] for c in categories]}, {current!r})')
        if message is not None:
            t.eq(merged['message'], message, f'message for {current!r}')


def test_humanFileSize(t):
    """SF-3.4: binary units, no decimal (sizes come from the links as strings)."""
    t.load()
    cases = [(1023, '1023 B'), (1024, '1 KiB'), (12288, '12 KiB'), (1048576, '1 MiB'),
             (734003200, '700 MiB'), (4294967296, '4 GiB'), ('1048576', '1 MiB')]
    for size, expected in cases:
        t.eq(t.call('humanFileSize', size, False, 0), expected, f'humanFileSize({size!r})')
