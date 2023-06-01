from . import parsing
from .util import log
import math


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
            final_rows = [self.title] + [''] + final_rows

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
