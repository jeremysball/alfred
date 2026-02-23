# Reference

Reference



rich.align

Align

Align.center()

Align.left()

Align.right()

VerticalCenter

rich.bar

Bar

rich.color

Color

Color.default()

Color.downgrade()

Color.from_ansi()

Color.from_rgb()

Color.from_triplet()

Color.get_ansi_codes()

Color.get_truecolor()

Color.is_default

Color.is_system_defined

Color.name

Color.number

Color.parse()

Color.system

Color.triplet

Color.type

ColorParseError

ColorSystem

ColorType

blend_rgb()

parse_rgb_hex()

rich.columns

Columns

Columns.add_renderable()

rich.console

Capture

Capture.get()

CaptureError

Console

Console.begin_capture()

Console.bell()

Console.capture()

Console.clear()

Console.clear_live()

Console.color_system

Console.control()

Console.encoding

Console.end_capture()

Console.export_html()

Console.export_svg()

Console.export_text()

Console.file

Console.get_style()

Console.height

Console.input()

Console.is_alt_screen

Console.is_dumb_terminal

Console.is_terminal

Console.line()

Console.log()

Console.measure()

Console.on_broken_pipe()

Console.options

Console.out()

Console.pager()

Console.pop_render_hook()

Console.pop_theme()

Console.print()

Console.print_exception()

Console.print_json()

Console.push_render_hook()

Console.push_theme()

Console.render()

Console.render_lines()

Console.render_str()

Console.rule()

Console.save_html()

Console.save_svg()

Console.save_text()

Console.screen()

Console.set_alt_screen()

Console.set_live()

Console.set_window_title()

Console.show_cursor()

Console.size

Console.status()

Console.update_screen()

Console.update_screen_lines()

Console.use_theme()

Console.width

ConsoleDimensions

ConsoleDimensions.height

ConsoleDimensions.width

ConsoleOptions

ConsoleOptions.ascii_only

ConsoleOptions.copy()

ConsoleOptions.encoding

ConsoleOptions.highlight

ConsoleOptions.is_terminal

ConsoleOptions.justify

ConsoleOptions.legacy_windows

ConsoleOptions.markup

ConsoleOptions.max_height

ConsoleOptions.max_width

ConsoleOptions.min_width

ConsoleOptions.no_wrap

ConsoleOptions.overflow

ConsoleOptions.reset_height()

ConsoleOptions.size

ConsoleOptions.update()

ConsoleOptions.update_dimensions()

ConsoleOptions.update_height()

ConsoleOptions.update_width()

ConsoleRenderable

ConsoleThreadLocals

Group

NewLine

PagerContext

RenderHook

RenderHook.process_renderables()

RenderableType

RichCast

ScreenContext

ScreenContext.update()

ScreenUpdate

ThemeContext

detect_legacy_windows()

group()

rich.emoji

Emoji

Emoji.replace()

rich.highlighter

Highlighter

Highlighter.__call__()

Highlighter.highlight()

ISO8601Highlighter

JSONHighlighter

JSONHighlighter.highlight()

NullHighlighter

NullHighlighter.highlight()

RegexHighlighter

RegexHighlighter.highlight()

ReprHighlighter

rich

get_console()

inspect()

print()

print_json()

reconfigure()

rich.json

JSON

JSON.from_data()

rich.layout

ColumnSplitter

ColumnSplitter.divide()

ColumnSplitter.get_tree_icon()

Layout

Layout.add_split()

Layout.children

Layout.get()

Layout.map

Layout.refresh_screen()

Layout.render()

Layout.renderable

Layout.split()

Layout.split_column()

Layout.split_row()

Layout.tree

Layout.unsplit()

Layout.update()

LayoutError

LayoutRender

LayoutRender.region

LayoutRender.render

NoSplitter

RowSplitter

RowSplitter.divide()

RowSplitter.get_tree_icon()

Splitter

Splitter.divide()

Splitter.get_tree_icon()

rich.live

Live

Live.is_started

Live.process_renderables()

Live.refresh()

Live.renderable

Live.start()

Live.stop()

Live.update()

rich.logging

RichHandler

RichHandler.HIGHLIGHTER_CLASS

RichHandler.emit()

RichHandler.get_level_text()

RichHandler.render()

RichHandler.render_message()

rich.markdown

BlockQuote

BlockQuote.on_child_close()

CodeBlock

CodeBlock.create()

Heading

Heading.create()

Heading.on_enter()

HorizontalRule

ImageItem

ImageItem.create()

ImageItem.on_enter()

Link

Link.create()

ListElement

ListElement.create()

ListElement.on_child_close()

ListItem

ListItem.on_child_close()

Markdown

MarkdownContext

MarkdownContext.current_style

MarkdownContext.enter_style()

MarkdownContext.leave_style()

MarkdownContext.on_text()

Paragraph

Paragraph.create()

TableBodyElement

TableBodyElement.on_child_close()

TableDataElement

TableDataElement.create()

TableDataElement.on_text()

TableElement

TableElement.on_child_close()

TableHeaderElement

TableHeaderElement.on_child_close()

TableRowElement

TableRowElement.on_child_close()

TextElement

TextElement.on_enter()

TextElement.on_leave()

TextElement.on_text()

UnknownElement

rich.markup

Tag

Tag.markup

Tag.name

Tag.parameters

escape()

render()

rich.measure

Measurement

Measurement.clamp()

Measurement.get()

Measurement.maximum

Measurement.minimum

Measurement.normalize()

Measurement.span

Measurement.with_maximum()

Measurement.with_minimum()

measure_renderables()

rich.padding

Padding

Padding.indent()

Padding.unpack()

rich.panel

Panel

Panel.fit()

rich.pretty

Node

Node.check_length()

Node.iter_tokens()

Node.render()

Pretty

install()

is_expandable()

pprint()

pretty_repr()

traverse()

rich.progress_bar

ProgressBar

ProgressBar.percentage_completed

ProgressBar.update()

rich.progress

BarColumn

BarColumn.render()

DownloadColumn

DownloadColumn.render()

FileSizeColumn

FileSizeColumn.render()

MofNCompleteColumn

MofNCompleteColumn.render()

Progress

Progress.add_task()

Progress.advance()

Progress.finished

Progress.get_default_columns()

Progress.get_renderable()

Progress.get_renderables()

Progress.make_tasks_table()

Progress.open()

Progress.refresh()

Progress.remove_task()

Progress.reset()

Progress.start()

Progress.start_task()

Progress.stop()

Progress.stop_task()

Progress.task_ids

Progress.tasks

Progress.track()

Progress.update()

Progress.wrap_file()

ProgressColumn

ProgressColumn.get_table_column()

ProgressColumn.render()

ProgressSample

ProgressSample.completed

ProgressSample.timestamp

RenderableColumn

RenderableColumn.render()

SpinnerColumn

SpinnerColumn.render()

SpinnerColumn.set_spinner()

Task

Task.completed

Task.description

Task.elapsed

Task.fields

Task.finished

Task.finished_speed

Task.finished_time

Task.get_time()

Task.id

Task.percentage

Task.remaining

Task.speed

Task.start_time

Task.started

Task.stop_time

Task.time_remaining

Task.total

Task.visible

TaskProgressColumn

TaskProgressColumn.render()

TaskProgressColumn.render_speed()

TextColumn

TextColumn.render()

TimeElapsedColumn

TimeElapsedColumn.render()

TimeRemainingColumn

TimeRemainingColumn.render()

TotalFileSizeColumn

TotalFileSizeColumn.render()

TransferSpeedColumn

TransferSpeedColumn.render()

open()

track()

wrap_file()

rich.prompt

Confirm

Confirm.process_response()

Confirm.render_default()

Confirm.response_type

FloatPrompt

FloatPrompt.response_type

IntPrompt

IntPrompt.response_type

InvalidResponse

Prompt

Prompt.response_type

PromptBase

PromptBase.ask()

PromptBase.check_choice()

PromptBase.get_input()

PromptBase.make_prompt()

PromptBase.on_validate_error()

PromptBase.pre_prompt()

PromptBase.process_response()

PromptBase.render_default()

PromptBase.response_type

PromptError

rich.protocol

is_renderable()

rich_cast()

rich.rule

Rule

rich.segment

ControlType

Segment

Segment.cell_length

Segment.adjust_line_length()

Segment.align_bottom()

Segment.align_middle()

Segment.align_top()

Segment.apply_style()

Segment.cell_length

Segment.control

Segment.divide()

Segment.filter_control()

Segment.get_line_length()

Segment.get_shape()

Segment.is_control

Segment.line()

Segment.remove_color()

Segment.set_shape()

Segment.simplify()

Segment.split_and_crop_lines()

Segment.split_cells()

Segment.split_lines()

Segment.strip_links()

Segment.strip_styles()

Segment.style

Segment.text

Segments

rich.spinner

Spinner

Spinner.render()

Spinner.update()

rich.status

Status

Status.console

Status.start()

Status.stop()

Status.update()

rich.style

Style

Style.background_style

Style.bgcolor

Style.chain()

Style.clear_meta_and_links()

Style.color

Style.combine()

Style.copy()

Style.from_color()

Style.from_meta()

Style.get_html_style()

Style.link

Style.link_id

Style.meta

Style.normalize()

Style.null()

Style.on()

Style.parse()

Style.pick_first()

Style.render()

Style.test()

Style.transparent_background

Style.update_link()

Style.without_color

StyleStack

StyleStack.current

StyleStack.pop()

StyleStack.push()

rich.styled

Styled

rich.syntax

Syntax

Syntax.default_lexer

Syntax.from_path()

Syntax.get_theme()

Syntax.guess_lexer()

Syntax.highlight()

Syntax.lexer

Syntax.stylize_range()

rich.table

Column

Column.cells

Column.copy()

Column.flexible

Column.footer

Column.footer_style

Column.header

Column.header_style

Column.highlight

Column.justify

Column.max_width

Column.min_width

Column.no_wrap

Column.overflow

Column.ratio

Column.style

Column.vertical

Column.width

Row

Row.end_section

Row.style

Table

Table.add_column()

Table.add_row()

Table.add_section()

Table.expand

Table.get_row_style()

Table.grid()

Table.padding

Table.row_count

rich.text

Text

Text.align()

Text.append()

Text.append_text()

Text.append_tokens()

Text.apply_meta()

Text.assemble()

Text.blank_copy()

Text.cell_len

Text.copy()

Text.copy_styles()

Text.detect_indentation()

Text.divide()

Text.expand_tabs()

Text.extend_style()

Text.fit()

Text.from_ansi()

Text.from_markup()

Text.get_style_at_offset()

Text.highlight_regex()

Text.highlight_words()

Text.join()

Text.markup

Text.on()

Text.pad()

Text.pad_left()

Text.pad_right()

Text.plain

Text.remove_suffix()

Text.render()

Text.right_crop()

Text.rstrip()

Text.rstrip_end()

Text.set_length()

Text.spans

Text.split()

Text.styled()

Text.stylize()

Text.stylize_before()

Text.truncate()

Text.with_indent_guides()

Text.wrap()

TextType

rich.theme

Theme

Theme.config

Theme.from_file()

Theme.read()

rich.traceback

Traceback

Traceback.extract()

Traceback.from_exception()

install()

rich.tree

Tree

Tree.ASCII_GUIDES

Tree.TREE_GUIDES

Tree.add()

rich.abc

RichRenderable