# aff/dic output

# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Hunspell Korean spellchecking dictionary.
#
# The Initial Developer of the Original Code is
# Changwoo Ryu.
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s): See CREDITS file
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

import sys
import unicodedata
import json

import config
import suffix
import josa
import encoding
from flags import *


def ENC(unistr):
    if config.internal_encoding == '2+RST':
        return encoding.encode(unistr)
    else:
        return unicodedata.normalize('NFD', unistr)


def warn(s):
    return sys.stderr.write(s + '\n')


def progress(s):
    return sys.stderr.write('Progress: ' + s + '...\n')


class Word:
    def __init__(self):
        self.word = ''
        self.pos = ''
        self.props = []
        self.stem = ''
        self.flags = []
        self.flags_alias = -1
        self.morph_alias = -1

    def __hash__(self):
        return (self.word + self.pos).__hash__()

    # to make it orderable
    def __lt__(self, other):
        if self.word < other.word:
            return True
        if self.pos < other.pos:
            return True
        # FIXME: 이렇게 하면 순서가 다를텐데. set에서 뭐가 먼저 나올지 알고...
        for prop in other.props:
            if prop not in self.props:
                return True
        return False

    def __repr__(self):
        return 'Word %s pos:%s' % (self.word, self.pos)

    def attach_flags(word):
        pos_default_flags = {
            '명사': [],
            '대명사': [],
            '특수:복수접미사': [plural_suffix_flag],
            '특수:알파벳': [alpha_flag],
            '특수:숫자': [digit_flag],
            '특수:수:1': [number_1_flag],
            '특수:수:10': [number_10_flag],
            '특수:수:100': [number_100_flag],
            '특수:수:1000': [number_1000_flag],
            '특수:수:10000': [number_10000_flag],
            '특수:고유수:1': [knumber_1_flag],
            '특수:고유수:10': [knumber_10_flag],
            '특수:금지어': [forbidden_flag],
            '내부:활용:-어': [conjugation_eo_flag],
            '내부:활용:-은': [conjugation_eun_flag],
            '내부:활용:-을': [conjugation_eul_flag],
        }
        try:
            word.flags = pos_default_flags[word.pos]
        except KeyError:
            pass
        if word.pos == '동사' or word.pos == '형용사':
            word.flags += suffix.find_flags(word.word, word.pos, word.props)
        word.flags += josa.find_flags(word.word, word.pos, word.props)
        prop_default_flags = {
            '단위명사': [counter_flag],
            '보조용언:-어': [auxiliary_eo_flag],
            '보조용언:-은': [auxiliary_eun_flag],
            '보조용언:-을': [auxiliary_eul_flag],
        }
        for prop in word.props:
            try:
                word.flags += prop_default_flags[prop]
            except KeyError:
                pass
        word.flags.sort()


class Dictionary:
    def __init__(self):
        self.words = set()
        self.flag_aliases = []
        self.morph_aliases = []

    def add(self, word):
        self.words.add(word)

    def remove(self, word):
        self.words.remove(word)

    def append(self, words):
        for w in words:
            self.words.add(w)

    def load_json(self, infile):
        d = json.load(infile)
        for entry in d['entries']:
            w = Word()
            w.word = entry['word']
            w.pos = entry['pos']
            if 'props' in entry:
                w.props = entry['props']
            if 'stem' in entry:
                w.stem = entry['stem']
            dic.add(w)

    def process(self):
        progress('복수형 확장')
        self.expand_plurals()
        if config.expand_auxiliary_attached:
            progress('플래그 계산')
            self.attach_flags()
            progress('보조용언 확장')
            self.expand_auxiliary()
        else:
            progress('보조용언 확장')
            self.expand_auxiliary()
            progress('플래그 계산')
            self.attach_flags()
        if config.output_word_morph:
            self.attach_morph()

    def output(self, afffile, dicfile):
        progress('dic 출력')
        self.output_dic(dicfile)
        progress('aff 출력')
        self.output_aff(afffile)

    ######################################################################

    def output_dic(self, outfile):
        outfile.write('%d\n' % len(self.words))
        for word in sorted(list(self.words)):
            line = '%s' % word.word
            if word.flags_alias > 0:
                line += ('/%d' % word.flags_alias)
            if config.output_word_stem:
                if word.stem:
                    line += (' st:%s' % word.stem)
            if config.output_word_morph:
                if word.morph_alias > 0:
                    line += (' %d' % word.morph_alias)
            line += '\n'
            outfile.write(ENC(line))

    def output_aff(self, outfile):
        from string import Template
        import aff
        template = Template(open('template.aff').read())

        # 주의: flag alias를 변경하므로 get_AF() 앞에 와야 한다.
        suffix_str = aff.get_suffix_defines(self.flag_aliases)
        josa_str = aff.get_josa_defines(self.flag_aliases)
        af_str = self.get_AF()
        am_str = self.get_AM()

        d = {'version': config.version,
             'required_hunspell': '%d.%d.%d' % config.required_hunspell_version,
             'CONV': aff.CONV_DEFINES,
             'AF': af_str,
             'AM': am_str,
             'forbidden_flag': str(forbidden_flag),
             'trychars': aff.TRYCHARS,
             'MAP': aff.MAP_DEFINES,
             'REP': aff.REP_DEFINES,
             'COMPOUNDRULE': aff.COMPOUNDRULE_DEFINES,
             'JOSA': josa_str,
             'SUFFIX': suffix_str, }
        outfile.write(template.substitute(d))

    def get_AF(self):
        aliases = self.flag_aliases
        result = 'AF %d\n' % len(aliases)
        for flags in aliases:
            result += 'AF %s\n' % ','.join('%d' % f for f in flags)
        return result

    def get_AM(self):
        aliases = self.morph_aliases
        result = 'AM %d\n' % len(aliases)
        for morph in aliases:
            result += 'AM %s\n' % morph
        return result

    ######################################################################

    def attach_flags(self):
        aliases = []
        for word in self.words:
            word.attach_flags()
            if word.flags:
                if word.flags not in aliases:
                    aliases.append(word.flags)
                word.flags_alias = aliases.index(word.flags) + 1
        self.flag_aliases = aliases

    def attach_morph(self):
        aliases = []
        for word in self.words:
            morph = ''
            if morph:
                if morph not in aliases:
                    aliases.append(morph)
                word.morph_alias = aliases.index(morph) + 1
        self.morph_aliases = aliases

    def expand_plurals(self):
        new_words = []
        for word in [w for w in self.words if '가산명사' in w.props]:
            new_word = Word()
            new_word.word = word.word + '들'
            new_word.pos = word.pos
            new_word.props = [p for p in word.props if p != '가산명사']
            new_word.stem = word.word
            new_words.append(new_word)
        self.append(new_words)

    def expand_auxiliary(self):
        new_words = []
        forms = ['-어', '-은', '-을']
        verbs = [w for w in self.words if w.pos in ['동사', '형용사']]
        for form in forms:
            auxiliaries = [w for w in verbs if ('보조용언:' + form) in w.props]
            for verb in verbs:
                # 본용언이 용언+용언 합성용언이면 붙여 쓸 수 없다
                if '용언합성' in verb.props:
                    continue
                prefixes = suffix.make_conjugations(verb.word,
                                                    verb.pos, verb.props, form)
                if config.expand_auxiliary_attached:
                    for auxiliary in auxiliaries:
                        # 본용언이 해당 보조용언으로 끝나는 합성어인 경우 생략
                        # 예: 다가오다 + 오다 => 다가와오다 (x)
                        if verb.word != auxiliary.word:
                            if verb.word.endswith(auxiliary.word):
                                continue
                        new_props = [p for p in auxiliary.props
                                     if not p.startswith('보조용언:')]
                        for prefix in prefixes:
                            new_word = Word()
                            new_word.word = prefix + auxiliary.word
                            new_word.pos = auxiliary.pos
                            new_word.stem = verb.word
                            new_word.props = new_props
                            new_word.flags = auxiliary.flags
                            new_word.flags_alias = auxiliary.flags_alias
                            new_words.append(new_word)
                else:
                    for prefix in prefixes:
                        new_word = Word()
                        new_word.word = prefix
                        new_word.stem = verb.word
                        new_word.pos = '내부:활용:' + form
                        new_words.append(new_word)
        self.append(new_words)

if __name__ == '__main__':
    afffilename = sys.argv[1]
    dicfilename = sys.argv[2]
    infilenames = sys.argv[3:]
    dic = Dictionary()
    for filename in infilenames:
        if filename.endswith('.json'):
            dic.load_json(open(filename, encoding='utf-8'))
        else:
            print('ERROR: unknown file type: ' + filename)
            sys.exit(1)
    dic.process()
    dic.output(open(afffilename, 'w', encoding='utf-8'),
               open(dicfilename, 'w', encoding='utf-8'))
