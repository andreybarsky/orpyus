from . import parsing, _settings
from .util import log
import math

#### this module handles ASCII display outputs
#### for e.g. showing chord diagrams in console

class Fretboard:
    """ a guitar fretboard display class that is initialised with its data
    and then called to display that data with some display parameters as ASCII

    nut display is different depending on where min_fret is cut off
    for example, open chord: 'x32010'
           E ‖---|---|---|--
           B ‖ C |---|---|--
           G ‖---|---|---|--
           D ‖   | E |---|--
           A ‖   |   | C |--
           E X   |   |   |--
               1   2   3

    or high chord: 'x5453x'
           E --|---|---|---|--
           B   | C |---|---|--
           G   |   |   | C |--
           D   |   | F#|---|--
           A   |   |   | D |--
           E X |   |   |   |--
                 3   4   5
    """

    def __init__(self, cells, index='EADGBE', highlight=None, mute=None, open=None, title=None, num_strings=6,
                 min_fret=None, max_fret=None):
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


    def disp(self, start_fret=None, end_fret=None, fret_size=None, continue_strings=False, fret_labels=True, index_width=None, align='cleft', fret_sep_char='¦', title=True, **kwargs):
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
        else:
            start_fret = start_fret if start_fret > 0 else 1

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
        highlight_chars = _settings.BRACKETS['fret_highlight']
        hl_left, hl_right = highlight_chars

        if start_fret == 1:
            open_leftborder    = '‖' # the nut
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
                elif (s, fret_num+1) in self.highlight and end_fret > fret_num:
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

    def column_widths(self, up_to_row=None, header=True):
        """return the max str size in each column, up to a specified row"""
        widths = []

        combi_chars_per_header = [sum([char in self._combi_chars for char in colname]) if type(colname)==str else 0  for colname in self.column_names]

        for col_num, col in self.column_data.items():
            cell_strs = [str(c) for c in col[:up_to_row]]
            combi_chars_per_cell = [sum([char in self._combi_chars for char in cell]) if type(cell)==str else 0  for cell in cell_strs]
            str_lens = [len(s)-combi_chars_per_cell[i] for i,s in enumerate(cell_strs)]
            if header:
                str_lens.extend([len(self.column_names[col_num]) - combi_chars_per_header[col_num]])
            widths.append(max(str_lens))
        return widths

    def total_width(self, up_to_row=None, header=True, margin_size=1):
        widths = self.column_widths(up_to_row=up_to_row, header=header)
        return sum(widths) + (self.num_columns-1)*margin_size # - sum(combi_chars_per_header)

    def show(self, title=None, title_pad_char='-', header=True, header_border=True,
             header_char='=', header_border_starts_at=None, header_start_char=None,
             align='left', margin=' ', fix_widths=False,
             max_rows=None, return_string=False,

             **kwargs):
        margin_size = len(margin)
        printed_rows = []

        widths = self.column_widths(up_to_row=max_rows, header=header)

        if fix_widths:
            # make all widths the same (e.g. for progressions)
            widths = [max(widths)] * len(widths)
        total_width = sum(widths) + ((self.num_columns-1)*len(margin))

        # must account for combining diacritics explicitly:
        # make header:
        combi_chars_per_header = [sum([char in self._combi_chars for char in colname]) if type(colname)==str else 0  for colname in self.column_names]
        if header:
            header_row = [f'{self.column_names[i]:{widths[i] + combi_chars_per_header[i]}}' for i in range(self.num_columns)]
            printed_rows.append(margin.join(header_row))

        if header_border:
            # total_width = self.total_width(up_to_row=max_rows, header=header, margin_size=margin_size)
            # total_width = sum(widths) + (self.num_columns-1)*margin_size # - sum(combi_chars_per_header)

            # allow for partial header, which stops being blank after a certain idx:
            if header_border_starts_at is None:
                header_border_starts_at = 0

            header_str = ' '*header_border_starts_at  +  header_char*(total_width - header_border_starts_at)
            # header_str = header_char*total_width

            if header_start_char is not None:
                # replace character in header string with desired starter char:
                # (this requires casting string to list and back again)
                header_lst = list(header_str)
                header_lst[header_border_starts_at] = header_start_char
                header_str = ''.join(header_lst)

            printed_rows.append(header_str)
        # else:
        #     total_width = self.total_width(up_to_row=max_rows, header=header, margin_size=margin_size)
        # make rows:
        for row in self.row_data[:max_rows]:
            combi_chars_per_cell = [sum([char in self._combi_chars for char in cell]) if type(cell)==str else 0  for cell in row]
            if align in ['r', 'right']:
                this_row = [f'{str(row[i]):>{widths[i] + combi_chars_per_cell[i]}}' for i in range(self.num_columns)]
            elif align in ['l', 'left']:
                this_row = [f'{str(row[i]):<{widths[i] + combi_chars_per_cell[i]}}' for i in range(self.num_columns)]
            else: # assume centre:
                this_row = [f'{str(row[i]):^{widths[i] + combi_chars_per_cell[i]}}' for i in range(self.num_columns)]

            printed_rows.append(margin.join(this_row))
        # finally, print result:
        # import ipdb; ipdb.set_trace()

        if title is not None:
            # pad title row with pad chars up to total width
            remaining_width = total_width - len(title)
            if remaining_width >= 2:
                left_width, right_width = int(math.floor(remaining_width/2)), int(math.ceil(remaining_width/2))
                left_pad = title_pad_char*(left_width-1) + ' '
                right_pad = ' ' + title_pad_char*(right_width-1)
                title = f'{left_pad}{title}{right_pad}'
            printed_rows = [title] + printed_rows

        final_string = '\n'.join(printed_rows)

        if not return_string:
            print(final_string)
        else:
            return final_string


    _combi_chars = set(_settings.DIACRITICS.values())


class Grid:
    """pure python implementation of a numpy-style 2darray (slow, but dependency-light)"""
    def __init__(self, shape: tuple[int,int], row_labels=None, col_labels=None):

        # check input:
        if type(shape) is int: # interpret single int shape "X" as square (X,X)
            shape = (shape, shape)
        elif len(shape) == 1: # same but unpack tuple/list
            assert type(shape[0]) is int
            shape = (shape[0], shape[0])
        else:
            assert type(shape[0]) is int and type(shape[1] is int)

        self.shape = shape
        self.num_rows, self.num_cols = shape


        self.row_labels = row_labels
        self.col_labels = col_labels

        # main attribute that contains the data indexed by row/col keys:
        self.data = {(r,c): None for r in range(self.num_rows) for c in range(self.num_cols)}
        self._update_arrays()

    def _update_arrays(self):
        """updates internal rows and cols attributes to synchronise with main self.data attr"""
        self.rows = [[self.data[(r,c)] for c in range(self.num_cols)] for r in range(self.num_rows)]
        self.cols = [[self.data[(r,c)] for r in range(self.num_rows)] for c in range(self.num_cols)]

    def __setitem__(self, key, values):
        """sets an item in this grid to any value.
            key must be a tuple of either ints or slices."""

        if type(key) is int:
            # only a single index: means entire row
            r = key
            c = slice(None, None, None)
        elif len(key) == 2:
            r,c = key
        else:
            raise KeyError(f'Did not understand key to __setitem__: {key}')

        if type(r) is int and type(c) is int:
            assert not isinstance(values, (tuple, list)) # must be single element
            value = values
            # simple setting of one element
            self.data[(r,c)] = value
            # cheap array update without needing to recompute everything:
            self.rows[r][c] = value
            self.cols[c][r] = value

        else:
            if type(r) is slice:
                row_idxs = range(self.num_rows)[r]
            elif r is None:
                row_idxs = range(self.num_rows)
            else:
                if r >= 0:
                    row_idxs = [r] # only a single row
                elif r < 0:
                    # negative indexing from end:
                    row_idxs = [self.num_rows + r]
                else:
                    raise Exception(f'did not understand row index: {r}')

            if type(c) is slice:
                col_idxs = range(self.num_cols)[c]
            elif r is None:
                col_idxs = range(self.num_cols)
            else:
                if c >= 0:
                    col_idxs = [c] # only a single column
                elif c < 0:
                    col_idxs = [self.num_cols + c]
                else:
                    raise Exception(f'did not understand col index: {c}')

            key_list = [(r,c) for r in row_idxs for c in col_idxs]

            if len(key_list) != 1 and isinstance(values, (list, tuple, range)):
                assert len(key_list) == len(values), f"{len(values)} values provided to set {len(key_list)} elements, must be the same"
                values = list(values)
            elif isinstance(values, (list, tuple, range)):
                # one key, but iterable of values
                assert len(values) == 1, f"only one item to set, but got {len(values)} values"
                values = values[0]
            else:
                # multiple keys, but one value
                # so broadcast it across as needed:
                values = [values]*len(key_list)

            for (r,c), val in zip(key_list, values):
                if (r,c) not in self.data.keys():
                    raise KeyError(f"Grid reference: {r,c}")
                self.data[(r, c)] = val
            # update arrays after setting:
            self._update_arrays()

    def __getitem__(self, *args):
        # unpack arguments if needed:
        if len(args) == 1:
            # row and column as a tuple
            key = args[0]
            if type(key) is int:
                # row only; assume all columns
                r = key
                c = slice(None)

            elif len(key) == 2:
                r, c = args[0]
            else:
                raise Exception(f'Did not understand key to __getitem__: {key}')

        elif len(args) == 2:
            # row and column as separate values:
            r, c = args

        if type(r) is int and type(c) is int:
            # simple indexing of one element: return bare value
            return self.data[(r,c)]

        if type(r) is slice:
            row_idxs = range(self.num_rows)[r]
        elif r is None:
            row_idxs = range(self.num_rows)
        else:
            row_idxs = [r] # only a single row

        if type(c) is slice:
            col_idxs = range(self.num_cols)[c]
        elif r is None:
            col_idxs = range(self.num_cols)
        else:
            col_idxs = [c] # only a single column

        # return values row by row, column by column:
        values = []
        for r_idx in row_idxs:
            row_data = self.rows[r_idx]
            for c_idx in col_idxs:
                cell_data = row_data[c_idx]
                values.append(cell_data)
                # values.append(self.data[r_idx, c_idx])
        return values

    def show(self, row_border=True, header_border=None, disp=True, margin=' ', **kwargs):
        # display as DataFrame
        num_output_cols = self.num_cols
        if self.col_labels is None:
            col_labels = ['' for _ in range(num_output_cols)]
        else:
            col_labels = [str(label) for label in self.col_labels]

        if self.row_labels is not None:
            # add an extra column to contain row labels:
            num_output_cols += 1
            col_labels = [''] + col_labels
            if row_border:
                # and another column for the margin
                num_output_cols += 1
                col_labels = [''] + col_labels

        disp_df = DataFrame(col_labels)
        for r, row in enumerate(self.rows):
            if self.row_labels is not None:
                if row_border:
                    # decide the row border character and insert it
                    # between labels and data:
                    if row_border is True:
                        row_border_char = '│'
                    else:
                        row_border_char = row_border
                    row_data = [self.row_labels[r], row_border_char] + row
                else:
                    # row labels but no border
                    row_data = [self.row_labels[r]] + row
                    row_border_char = None
            else:
                row_data = row
                row_border_char = None
            disp_df.append(row_data)

        has_header = (self.col_labels is not None)
        if header_border is None:
            header_border = has_header
        if header_border is True:
            # decide the header char, defaulting to ─
            header_char = '─'
        else:
            header_char = header_border
        if has_header:
            # header border starts at whatever the row label column's width is
            if self.row_labels is not None:
                widths = disp_df.column_widths()
                header_border_start = widths[0] + len(margin)
            else:
                header_border_start = 0
        else:
            header_border_start = None

        if header_char == '─' and row_border_char == '│' and header_border_start > 0:
            header_start_char = '┌' # corner char (unicode box drawing)

        else:
            header_start_char = None

        output_str = disp_df.show(return_string=True, header=has_header, header_char=header_char, header_border=header_border,
                                  header_start_char=header_start_char, header_border_starts_at=header_border_start,
                                  margin=margin,
                                  **kwargs)
        if disp:
            print(output_str)
        else:
            return output_str

    def __str__(self):
        return self.show(disp=False)

    def __repr__(self):
        return str(self)

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
                            'null': [''],
                          'border': ['']
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
            elif col_name == 'null':
                df_row.append('')
            elif col_name == 'border':
                df_row.append('|')

        df.append(df_row)

    df.show(max_rows=max_results, **kwargs)




class Keyboard:
    pass
    ### TBI, need to work out a nice way to present this

    # # example: (5-char keys)
    # | C  Db  D Eb   E   F  Gb  G  Ab A  Bb B     C  Db D  Eb E     F  Gb G  Ab A  Ab B    C |
    # |░░░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░|▓▓▓|░|▓▓▓|░░░|░░░|
    # |░░░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░|▓▓▓|░|▓▓▓|░░░|░░░|
    # |░░░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░|▓▓▓|░░░|░░░|▓▓▓|░|▓▓▓|░|▓▓▓|░░░|░░░|
    # |░░░░░|░░░░░|░░░░░|░░░░░|░░░░░|░░░░░|░░░░░|░░░░░|░░░░░|░░░░░|░░░░░|░░░░░|░░░░░|░░░░░|░░░|
    # |  C  Db D  Eb E     F  Gb G  Ab A  Bb B     C  Db D  Eb E     F  Gb G  Ab A  Ab B    C |

    # # 3-char keys:
    # |   Db  Eb      Gb  Ab  Bb  |   Db  Eb      Gb  Ab  Bb  |
    # |░░|▓|░|▓|░░|░░|▓|░|▓|░|▓|░░|░░|▓|░|▓|░░|░░|▓|░|▓|░|▓|░░|
    # |░░|▓|░|▓|░░|░░|▓|░|▓|░|▓|░░|░░|▓|░|▓|░░|░░|▓|░|▓|░|▓|░░|
    # |░░|▓|░|▓|░░|░░|▓|░|▓|░|▓|░░|░░|▓|░|▓|░░|░░|▓|░|▓|░|▓|░░|
    # |░░░|░░░|░░░|░░░|░░░|░░░|░░░|░░░|░░░|░░░|░░░|░░░|░░░|░░░|
    # | C   D   E   F   G   A   B | C   D   E   F   G   A   B |

    # □■
