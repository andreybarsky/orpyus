from . import parsing, _settings
from .util import log
import math

class Keyboard:
    ...
    # example:
    # | C  Db  D Eb   E   F  Gb  G  Ab  A Ab   B   C  Db  D Eb   E   F  Gb  G  Ab  A Ab   B   C |
    # |░░░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░░|▓▓▓|░|▓▓▓|░░░|░░░|
    # |░░░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░░|▓▓▓|░|▓▓▓|░░░|░░░|
    # |░░░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░░|▓▓▓|░|▓▓▓|░░░|░░░|
    # |░░░░░|░░░░░|░░░░░|░░░░░|░░░░░░|░░░░░|░░░░░|░░░░░|░░░░░|░░░░░|░░░░░|░░░░░░|░░░░░|░░░░░|░░░|
    # | C  Db  D Eb   E   F  Gb  G  Ab  A Ab   B   C  Db  D Eb   E   F  Gb  G  Ab  A Ab   B   C |

    # □■

class Fretboard:
    ### a guitar fretboard display class that is initialised with its data
    ### and then called to display that data with some display parameters

    # example:
    ### open chord:
    #        E |---|---|---|--
    #        B | C |---|---|--
    #        G |---|---|---|--
    #        D |   | E |---|--
    #        A |   |   | C |--
    #        E X   |   |   |--
    #            1   2   3
    #
    #        ### high chord: x5453x
    #        E --|---|---|---|--
    #        B   | C |---|---|--
    #        G   |   |   | C |--
    #        D   |   | F#|---|--
    #        A   |   |   | D |--
    #        E X |   |   |   |--
    #              3   4   5

    def __init__(self, cells, index='EADGBE', highlight=None, mute=None, open=None, title=None, num_strings=6):
        """args:
        cells: a dict that keys (string,fret) tuples to the contents of what should be displayed in that fret.
            note that strings are indexed from 1, as in guitar terminology: low E is "first string".
            frets are *also* indexed from 1, but there is still a fret 0, i.e. open string.
        highlight_cells: a list of (string,fret) tuples to highlight
            in addition to whatever contents they might or might not have.
        index: labels to display at left of fretboard (from bottom to top). 'EADGBE' by default.
        mute: list of rows to display mute markers (X) next to (from bottom to top). by default, any that don't turn up in 'cells'.
        open: same as mute, but controls whether to display string continuations (if continue_strings is True)
        continue_strings: if True, display string continuation from the rightmost occupied fret for each string."""


        self.index = index if isinstance(index, (list, tuple)) else parsing.parse_out_note_names(index)
        self.mute = [] if mute is None else mute

        self.title = str(title)
        self.num_strings = num_strings

        self.cells = cells
        self.strings_used, self.frets_used = zip(*self.cells.keys())
        self.string_contents = {s: {f: self.cells[s,f]} for s,f in self.cells.keys()}
        self.fret_contents = {f: {s: self.cells[s,f]} for s,f in self.cells.keys()}
        self.all_contents = list(self.cells.values())

        # we expect highlight to be a list of integer tuples,
        # but if we've been passed a pair of ints by accident, quietly re-cast them:
        if highlight is not None and isinstance(highlight[0], int):
            self.highlight = [highlight]
        elif highlight is not None:
            self.highlight = highlight
        else:
            self.highlight = []

        ### get min and max extent of fretting positions, but be sensitive to all 0s:
        self.max_fret = max(self.frets_used)
        self.min_fret = 0 if self.max_fret == 0 else min([f for f in self.frets_used if f != 0]) # minimum nonzero fret

        if open is None:
            self.open = [s for s in range(1, num_strings+1) if (s not in self.mute) and (s not in self.strings_used)]
        else:
            self.open = open


    def disp(self, start_fret=None, end_fret=None, fret_size=None, continue_strings=False, fret_labels=True, index_width=None, align='cleft', fret_sep_char='¦', title=True):
        """displays data between min_fret and max_fret (detects from data respectively if either are None),
        and leaves fret_size between each vertical fret bar (defaults to max([3,max(len(data))]) if None)

        align must be one of: 'left', 'right', 'cleft' or 'cright'. Latter two align to centre, but rounding left or right."""

        ############## determine length of diagram:

        # for e.g. open chords:
        if start_fret is None:
            if self.max_fret <= 4:
                start_fret = 1
            # for e.g. chords high on the neck:
            elif self.min_fret >= 4:
                # truncate length of diagram by starting on minimum fret
                # (but if min fret is already 3 or less, just go to 1 anyway)
                start_fret = self.min_fret
            # for whole fretboard diagrams:
            else:
                # go from 1 to the very end
                start_fret = 1

        if end_fret is None:
            end_fret = max([self.max_fret+1, 3]) # at least 3, otherwise 1 more than max fret

        num_frets_shown = (end_fret - start_fret) + 1

        log(f'Start fret: {start_fret}, end fret: {end_fret}')

        if fret_size is None:
            # use the max of the string data, or 4, whichever is greater:
            maxlen = max([len(str(c)) for c in self.all_contents])
            fret_size = max([maxlen, 4])

        if index_width is None:
            index_width = max([len(str(i)) for i in self.index]) + 1

        ############## define surrounding contents, sepchars etc.:

        # fret_sep_char = '|'
        assert len(fret_sep_char) == 1
        highlight_chars = '⟦⟧'
        # highlight_chars = '‖‖'
        hl_left, hl_right = highlight_chars

        if start_fret == 1:
            open_leftborder    = '‖'
            played_leftborder  = '‖'
            muted_leftborder   = 'X'
            footer_leftborder   = ' ' * (index_width-1)
        else:
            open_leftborder    = f'--{fret_sep_char}' if continue_strings else f'  {fret_sep_char}'
            played_leftborder  = f'  {fret_sep_char}'
            muted_leftborder   = f'X {fret_sep_char}'
            footer_leftborder   = '   '

        sounded_rightborder = '--' if continue_strings else '  '
        muted_rightborder   = '  '

        empty_fret =   ' ' * fret_size
        sounded_fret = '-' * fret_size
        # empty_idx =    ' ' * (fret_size+1)

        ############## start piecing together contents

        string_rows = []
        string_margins = []

        ####### loop across strings:
        for s in range(1,self.num_strings+1):
            # left border contains the index, right contains either nothing or a string continuation
            string_is_muted = s in self.mute
            string_is_open = s in self.open

            # if continue_strings, we need to know where the string continues up to:
            if continue_strings and not string_is_open:
                if s in self.strings_used:
                    this_string_min_fret = min([f for f in self.string_contents[s].keys() if f != 0])
                    this_string_max_fret = max([f for f in self.string_contents[s].keys() if f != 0])
                elif string_is_muted:
                    this_string_min_fret = 0
                    this_string_max_fret = 99

            ####### loop across frets and define string contents:
            this_string_row = []
            for f in range(num_frets_shown):
                fret_num = start_fret+f
                cell_key = (s, fret_num)
                if cell_key in self.cells:
                    ######################################################
                    # this cell has content: figure out how to space it
                    content = self.cells[cell_key]
                    if len(content) == fret_size:
                        # if it fits perfectly in the cell, put it there:
                        this_cell = content
                    else:
                        # otherwise centre it, filling right before left:
                        remaining_space = fret_size - len(content)
                        ### TBI: fix this later
                        if align in ['cleft', 'centre', 'center']:
                            left_space = remaining_space // 2
                        elif align == 'cright':
                            left_space = math.ceil(remaining_space/2)
                        elif align == 'left':
                            left_space = 0
                        elif align == 'right':
                            left_space = remaining_space
                        else:
                            print(f"arg 'align' to Fretboard.disp must be one of: left, right, cleft, cright")
                        content_space = fret_size - left_space
                        # if continue_strings and fret_num == this_string_min_fret:
                            # left_str = ' '*left_space
                        # else:
                        left_str = ' '*left_space
                        this_cell = f'{left_str}{content:{content_space}}'
                    ######################################################
                else:
                    # this cell has no content, it is empty
                    if continue_strings and (string_is_open or fret_num > this_string_max_fret):
                        this_cell = sounded_fret
                    else:
                        this_cell = empty_fret

                # determine left/right borders of cell:
                # if this cell is highlighted, sep char needs to be a right highlight:
                if cell_key in self.highlight:
                    log(f'highlighting {cell_key}')
                    sep_char = hl_right
                # if the NEXT cell is highlighted, must be a left highlight:
                elif (s, fret_num+1) in self.highlight:
                    log(f'pre-highlighting {(s, fret_num+1)} from {cell_key}')
                    sep_char = hl_left
                else:
                    # otherwise normal fret separator
                    sep_char = fret_sep_char

                this_string_row.append(this_cell + sep_char)

            string_rows.append(this_string_row)

            ####### define borders
            if string_is_muted:
                this_string_leftborder = muted_leftborder
                this_string_rightborder = muted_rightborder
            elif string_is_open:
                this_string_leftborder = open_leftborder
                this_string_rightborder = sounded_rightborder
            else:
                this_string_leftborder = played_leftborder
                this_string_rightborder = sounded_rightborder

            # detect if fret 0 (the index) of this string has been highlighted:
            if fret_labels:
                if ((s,0) in self.highlight) and (start_fret==1):
                    # and if so, replace its fret_sep_char with a right highlight
                    this_string_leftborder = this_string_leftborder[:-1] + hl_right
                elif (s,start_fret) in self.highlight:
                    # if fret _1_ is highlighted, needs to be a left highlight instead:
                    this_string_leftborder = this_string_leftborder[:-1] + hl_left

            this_string_index = self.index[s-1]
            this_string_leftmargin = f'{this_string_index:{index_width}}{this_string_leftborder}'


            # this_string_rightmargin = fret_sep_char + this_string_rightborder

            string_margins.append((this_string_leftmargin, this_string_rightborder))

        # now turn strings upside down:
        string_rows = list(reversed(string_rows))
        string_margins = list(reversed(string_margins))

        # join cell contents and pad with left/right margins:
        final_rows = [string_margins[r][0] + ''.join(string_rows[r]) + string_margins[r][1] for r in range(self.num_strings)]

        if title and (self.title is not None):
            final_rows = [self.title] + final_rows

        # and finally put fret labels on the bottom if needed:
        if fret_labels:

            # footer_leftmargin = ('o'*index_width) + footer_leftborder

            left_space = 1 # remaining_space // 2
            content_space = fret_size - left_space
            footer_cells = [f'{" ":{left_space}}{(start_fret + (f)):{content_space}}' for f in range(num_frets_shown)]

            final_fret_row = footer_leftborder + ' '.join(footer_cells)
            final_rows.append(final_fret_row)
        # print the final result:
        print('\n'.join(final_rows))


class DataFrame:
    def __init__(self, colnames):
        self.column_names = colnames
        self.num_columns = len(colnames)
        self.column_data = {i:[] for i in range(self.num_columns)}

        self.row_data = []
        self.num_rows = 0

    def append(self, data_lst):
        """add a row of data to this dataframe, which we store as objects"""
        assert len(data_lst) == self.num_columns, f"tried to append row of length {len(data_lst)} but dataframe has {self.num_columns} columns"
        row = data_lst
        self.row_data.append(row)
        self.num_rows += 1

        for i, item in enumerate(row):
            self.column_data[i].append(item)

    def __len__(self):
        """DataFrame length is the number of rows"""
        return self.num_rows

    def column_widths(self, up_to_row=None):
        """return the max str size in each column, up to a specified row"""
        widths = []


        for col_num, col in self.column_data.items():
            col_strs = [str(c) for c in col[:up_to_row]]
            str_lens = [len(s) for s in col_strs] + [len(self.column_names[col_num])]
            widths.append(max(str_lens))
        return widths

    def show(self, margin=' ', header_border=True, max_rows=None):
        margin_size = len(margin)
        printed_rows = []
        widths = self.column_widths(up_to_row=max_rows)
        combi_chars = {"\u0324", "\u0323", "\u0307", "\u0308"} # a kludge: we have to count combining characters separately for chord notelist formatting
        # make header:
        header_row = [f'{self.column_names[i]:{widths[i]}}' for i in range(self.num_columns)]
        printed_rows.append(margin.join(header_row))
        if header_border:
            total_width = sum(widths) + (self.num_columns-1)*margin_size
            printed_rows.append('='*total_width)
        # make rows:
        for row in self.row_data[:max_rows]:
            combi_chars_per_cell = [sum([char in combi_chars for char in cell]) if type(cell)==str else 0  for cell in row]
            this_row = [f'{str(row[i]):{widths[i] + combi_chars_per_cell[i]}}' for i in range(self.num_columns)]
            printed_rows.append(margin.join(this_row))
        # finally, print result:
        print('\n'.join(printed_rows))

def chord_table(chords, columns=['chord', 'intervals', 'tertian', 'degrees'],
                parent_scale=None, parent_degree=None, # can parent_degree be 'idx'?
                scores=None, max_results=None, **kwargs):
    df_cols = []
    col_name_lookup = {    'chord': ['Chord'],
                           'idx'  : [''],
                       'intervals': ['Intervals'],
                           'notes': ['Notes'],
                         'factors': ['Factors'],
                         'degrees': ['Degrees'],
                            'tert': ['Tert.'],
                            'likl': ['Likl.'],
                            'cons': ['Cons.'],
                             'rec': ['Rec.'],
                            'prec': ['Prec.'],
                      }

    for col_name in columns:
        df_cols.extend(col_name_lookup[col_name])

    if parent_scale is not None and parent_degree is not None and parent_degree != 'idx':
        root_interval = parent_scale.get_interval_from_degree(parent_degree)

    df = DataFrame(df_cols)
    for i, chord in enumerate(chords):
        df_row = []
        if parent_scale is not None:
            if parent_degree == 'idx':
                root_interval = parent_scale.get_interval_from_degree(i+1)
            chord_intervals_wrt_scale = [(iv + root_interval).flatten() for iv in chord.intervals]
            if parent_scale.is_irregular():
                # recast to appropriate IrregularIntervals if needed:
                irreg_obj = parent_scale.intervals[0]
                chord_intervals_wrt_scale = [irreg_obj.re_cache(iv.value) for iv in chord_intervals_wrt_scale]
        if scores is not None:
            if type(scores) == dict:
                chord_scores = scores[chord]
            elif type(scores) == list:
                chord_scores = scores[i]

        clb, crb = _settings.BRACKETS['chromatic_intervals']

        for col_name in columns:
            # separate out intervallist/notelist brackets into their own columns:
            # (just for neatness/alignment)
            if col_name == 'chord':
                df_row.extend([chord.name])
            elif col_name == 'idx':
                df_row.extend([str(i+1)])

            elif col_name == 'intervals':
                illb, ilrb = chord.intervals._brackets
                intervals_str = str(chord.intervals)[1:-1]

                # annotate chromatic intervals:
                if parent_scale is not None and len(parent_scale.chromatic_intervals) > 0:
                    ivlb, ivrb = _settings.BRACKETS['Interval']
                    for iv in parent_scale.chromatic_intervals:
                        iv_short = iv.short_name[1:-1] # interval short name without surrounding brackets
                        intervals_str = intervals_str.replace(f'{ivlb}{iv_short}{ivrb}', f'{clb}{iv_short}{crb}')

                # df_row.extend([illb, intervals_str, ilrb])
                df_row.extend([intervals_str])

            elif col_name == 'notes':
                nlb, nrb = chord.notes._brackets
                notes_str = chord._dotted_notes(markers=False)

                # annotate chromatic notes:
                if parent_scale is not None and len(parent_scale.chromatic_intervals) > 0:
                    chrom_idxs = parent_scale.which_intervals_chromatic()
                    scale_chrom_notes = [n for i,n in enumerate(parent_scale.notes) if chrom_idxs[i]]
                    for n in scale_chrom_notes:
                        notes_str = notes_str.replace(n.name, f'{clb}{n.name}{crb}')

                # df_row.extend([nlb, notes_str, nrb])
                df_row.extend([notes_str])
            elif col_name == 'factors':
                flb, frb = ScaleFactors._brackets
                factors = [iv.factor_name if iv not in parent_scale.chromatic_intervals else f'{clb}{iv.factor_name}{crb}' for iv in chord_intervals_wrt_scale]
                factors_str = ', '.join(factors)
                # df_row.extend([flb, factors_str, frb])
                df_row.extend([factors_str])

            elif col_name == 'degrees':
                cmark = _settings.CHARACTERS['chromatic_degree']
                scale_degs = [str(int(parent_scale.interval_degrees[iv]))  if iv not in parent_scale.chromatic_intervals else cmark for iv in chord_intervals_wrt_scale]
                scale_degs_str = ', '.join(scale_degs)
                df_row.append(scale_degs_str)
            elif col_name == 'tert':
                if chord.is_tertian():
                    tert_str = _settings.CHARACTERS['true']
                elif chord.is_inverted_tertian():
                    tert_str = _settings.CHARACTERS['somewhat']
                else:
                    tert_str = ' '
                df_row.append('  ' + tert_str)
            elif col_name == 'likl':
                likl = chord.likelihood
                df_row.append(f' {likl:.2f}')
            elif col_name == 'cons':
                cons = chord.consonance
                df_row.append(f'{cons:.3f}')
            elif col_name == 'rec':
                df_row.append(chord_scores['recall'])
            elif col_name == 'prec':
                df_row.append(chord_scores['precision'])

        df.append(df_row)

    df.show(max_rows=max_results, **kwargs)
