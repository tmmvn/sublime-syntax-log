# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Author : yongchan jeon (Kris) poucotm@gmail.com
# File   : Log Highlight.py
# Create : 2020-07-11 09:12:01
# Editor : sublime text3, tab size (4)
# -----------------------------------------------------------------------------

import sublime
import sublime_plugin
import re
import threading
import os
import traceback
import plistlib
import shutil


# relative path searching
MAX_SCAN_PATH     = 1000
MAX_STAIR_UP_PATH = 10
# refresh delay
REFRESH_WAIT = 500  # 0.5s
# to handle extension
EXT_ALL = []
EXT_DIC = {}
OUT_DIC = {}
# regular expresson constants
LINK_REGX_PLIST    = r"""["']?[\w\d\:\\\/\.\-\=]+\.\w+[\w\d]*["']?\s*[,:on line\(]{1,9}\s*\d+\)?\:?(\d+)?"""
LINK_REGX_SETTING  = r"""(["']?[\w\d\:\\\/\.\-\=]+\.\w+[\w\d]*["']?\s*[,:on line\(]{1,9}\s*\d+\)?\:?(\d+)?)"""
LINK_REGX_RESULT   = r"""["']?([\w\d\:\\\/\.\-\=]+\.\w+[\w\d]*)["']?\s*[,:on line\(]{1,9}\s*(\d+)\:?(\d+)?"""
LINK_REGX_RELPATH  = r"""["']?([\w\d\:\\\/\.\-\=]+\.\w+[\w\d]*)["']?\s*[,:on line\(]{1,9}\s*\d+\)?"""
LINK_REGX_SUMMARY  = r"""(?:["']?[\w\d\:\\\/\.\-\=]+\.\w+[\w\d]*["']?\s*[,:on line\(]{1,9}\s*\d+\)?\:?(\d+)?)"""
QUOTE_REGX_PLIST   = r"""(["'])(?:(?=(\\?))\2.)*?\1"""
QUOTE_REGX_SETTING = r"""(["'].+?["'])"""
QUOTE_REGX_SUMMARY = r"""(?:["'].+?["'])"""
# to prevent re-run in short time
IS_WORKING = False
IS_WAITING = False
# managing views
LOGH_VIEW  = []
LOGH_LASTV = -1


def plugin_loaded():
    loaded()


def loaded():
    # default tmTheme
    #gen_tmtheme()
    # update log extension/panel list
    get_log_extension()
    # register callback
    lhs = get_prefs()
    lhs.clear_on_change('lh-prefs')
    lhs.add_on_change('lh-prefs', get_log_extension)
    # check all log-highlited views
    check_logh_views()


def get_prefs():
    return sublime.load_settings('Log Highlight.sublime-settings')


def get_log_property(log_name, prop, default):
    return get_prefs().get('log_list').get(log_name).get(prop, default)


def get_log_extension():
    global EXT_ALL
    global EXT_DIC
    global OUT_DIC
    EXT_ALL = []
    EXT_DIC = {}
    OUT_DIC = {}
    lol = get_prefs().get('log_list')
    lgl = list(lol.keys())
    for ltype in lgl:
        extl = lol.get(ltype).get('extension')
        for ext in extl:
            EXT_ALL.append(ext)
            EXT_DIC[ext] = ltype
        outl = lol.get(ltype).get('output.panel')
        for out in outl:
            OUT_DIC[out] = ltype
    return


def get_log_name(view):
    if view.name() == "":
        isfile = True
        _name  = view.file_name()
    else:
        isfile = False
        _name  = view.name()
    if not _name:
        return None
    basen = os.path.basename(_name).lower() if isfile else _name
    exdic = list(EXT_DIC.keys())
    for ext in exdic:
        if ext[-1] == '*' and basen.startswith(ext[0:-1]):
            return EXT_DIC[ext]
        elif ext[0] == '*' and basen.endswith(ext[1:len(ext)]):
            return EXT_DIC[ext]
        elif basen.endswith(ext):
            return EXT_DIC[ext]
    return None


def check_view_log(view):
    if view.name() == "":
        isfile = True
        _name  = view.file_name()
    else:
        isfile = False
        _name  = view.name()
    if not _name:
        return None
    basen = os.path.basename(_name).lower() if isfile else _name
    for ext in EXT_ALL:
        if ext[-1] == '*' and basen.startswith(ext[0:-1]):
            return True
        elif ext[0] == '*' and basen.endswith(ext[1:len(ext)]):
            return True
        elif basen.endswith(ext):
            return True
    return False


def check_logh_views():
    winsl = sublime.windows()
    global LOGH_VIEW
    for w in winsl:
        viewl = w.views()
        for v in viewl:
            if check_syntax(v):
                LOGH_VIEW.append([v.id(), 0])
            if v.settings().get('logh_lastv') is True:
                global LOGH_LASTV
                LOGH_LASTV = v.id()
    return


def get_style():
    aview = sublime.active_window().active_view()
    prefs = sublime.load_settings("Preferences.sublime-settings")
    cschm = prefs.get('color_scheme')
    viewc = '' if aview is None else aview.settings().get('color_scheme')
    if aview is None or cschm != viewc:
        view = sublime.active_window().new_file()
        style = view.style()
        sublime.active_window().focus_view(view)
        sublime.active_window().run_command('close_file')
        return style
    else:
        return aview.style()


def get_background():
    bgclr = '#000000'
    global STV
    if STV >= 3150:
        style = get_style()
        bgclr = style.get('background')
    else:
        prefs = sublime.load_settings("Preferences.sublime-settings")
        cschm = prefs.get('color_scheme')
        cstxt = str(sublime.load_resource(cschm))
        treep = plistlib.readPlistFromBytes(cstxt.encode())
        bgclr = treep['settings'][0]['settings']['background']
    return bgclr


def get_severity_list(log_name):
    lgn = get_prefs().get('log_list').get(log_name)
    svt = lgn.get('severity')
    svl = []
    for i, k in enumerate(list(svt.keys())):
        if (svt.get(k)).get('enable', False):
            svl.append(k)
    return svt, svl


def check_syntax(view):
    syn = view.settings().get('syntax', '')
    if isinstance(syn, str):
        if syn.endswith('.tmLanguage'):
            return True
        else:
            return False
    else:
        return False


# def gen_tmtheme():
#     etheme = os.path.join(sublime.packages_path(), 'User', 'Log Highlight', 'default.tmTheme')
#     if not os.path.exists(etheme):
#         uspath = os.path.join(sublime.packages_path(), 'User', 'Log Highlight')
#         if not os.path.exists(uspath):
#             os.makedirs(uspath)
#         otheme = sublime.load_resource('Packages/Log Highlight/Log Highlight.tmTheme')
#         uspath = os.path.join(sublime.packages_path(), 'User', 'Log Highlight', 'default.tmTheme')
#         fwrite(uspath, otheme)


# def change_bgcolor(tmTheme, bgcolor):
#     tree = plistlib.readPlist(tmTheme)
#     tree['settings'][0]['settings']['background'] = bgcolor
#     plistlib.writePlist(tree, tmTheme)


# def set_as_default_theme(view):
#     view.settings().set('color_scheme', 'Packages/User/Log Highlight/default.tmTheme')


def set_syntax_theme(view, log_name):
    syntax = os.path.join(sublime.packages_path(), 'SyntaxLog', 'Log Highlight.tmLanguage')
    view.set_syntax_file(syntax)
    # bgclr  = get_background()
    # etheme = os.path.join(sublime.packages_path(), 'User', 'Log Highlight', 'default.tmTheme')
    # ltheme = os.path.join(sublime.packages_path(), 'User', 'Log Highlight', ltitle + '.tmTheme')
    # if os.path.exists(ltheme):
    #     change_bgcolor(ltheme, bgclr)
    #     view.settings().set('color_scheme', 'Packages/User/Log Highlight/' + ltitle + '.tmTheme')
    # else:
    #     if not os.path.exists(etheme):
    #         gen_tmtheme()
    #         change_bgcolor(etheme, bgclr)
    #         sublime.set_timeout_async(lambda: set_as_default_theme(view), 0)
    #     else:
    #         change_bgcolor(etheme, bgclr)
    #set_as_default_theme(view)


# def fwrite(fname, text):
#     try:
#         with open(fname, "w", newline="") as f:
#             f.write(text)
#     except Exception:
#         disp_exept()


# def fread(fname):
#     text = ""
#     try:
#         with open(fname, "r") as f:
#             text = str(f.read())
#     except Exception:
#         disp_exept()
#         return text


def disp_msg(msg):
    sublime.status_message(' Log Highlight : ' + msg)


def disp_error(msg):
    sublime.status_message(' Log Highlight : ' + msg)


def disp_exept():
    print ('LOG HIGHLIGHT : ERROR _______________________________________')
    traceback.print_exc()
    print ('=============================================================')
    disp_error("Error is occured. Please, see the trace-back information in Python console.")


class LogHighlightCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        lname = self.view.settings().get('log_name')
        if not lname:
            lname = get_log_name(self.view)
            self.view.settings().set('log_name', lname)
            if not lname:
                return
        ltype = get_log_property(lname, 'type', 'system')
        if isinstance(ltype, str) and ltype == 'system':
            set_syntax_theme(self.view, lname)
            return
        # workaround for ST3 result_file_regex bug
        ulink = get_log_property(lname, 'use_link', True)
        if ulink:
            self.view.settings().set('result_file_regex', LINK_REGX_RESULT)
        global IS_WORKING
        if IS_WORKING:
            return
        lthread = LogHighlightThread(self.view, True)
        lthread.start()

    def is_visible(self):
        lhs = get_prefs()
        if not lhs.get("context_menu", True):
            return False
        try:
            # unknow view also passed (like output window)
            if self.view.file_name() is None:
                return True
            return check_view_log(self.view)
        except Exception:
            return False


class LogHighlightEvent(sublime_plugin.EventListener):

    def on_new_async(self, view):
        self.auto_highlight(view)

    def on_load_async(self, view):
        self.auto_highlight(view)

    # def on_activated_async(self, view):
    #     if view.settings().get('is_widget'):
    #         self.auto_highlight(view)

    def on_modified_async(self, view):
        global LOGH_VIEW
        for i, vid in enumerate(LOGH_VIEW):
            if view.id() == vid[0] or view.is_loading():
                LOGH_VIEW[i][1] = LOGH_VIEW[i][1] + 1
                global IS_WAITING
                if not IS_WAITING:
                    thread = LogHighlightRefreshThread(view)
                    thread.start()
                break
        return

    def on_post_window_command(self, view, command_name, args):
        if command_name == 'show_panel' and 'panel' in args.keys():
            lhs  = get_prefs()
            auth = lhs.get("auto_highlight", False)
            if not auth:
                return
            outl = lhs.get("auto_highlight_output_panel", None)
            outp = [e for e in outl if 'output.'+e == args['panel']]
            if len(outp) > 0:
                logn = OUT_DIC[outp[0]]
                if logn:
                    pview = view.find_output_panel(outp[0])
                    if not check_syntax(pview):
                        pview.settings().set('panel', outp[0])
                        pview.settings().set('log_name', logn)
                        pview.run_command("log_highlight")
        return

    def on_close(self, view):
        for vid in LOGH_VIEW:
            if view.id() == vid[0]:
                LOGH_VIEW.remove(vid)
            break
        global LOGH_LASTV
        if view.id() == LOGH_LASTV:
            if len(LOGH_VIEW) > 0:
                LOGH_LASTV = LOGH_VIEW[-1]
            else:
                LOGH_LASTV = -1
        return

    def auto_highlight(self, view):
        lhs  = get_prefs()
        auth = lhs.get("auto_highlight", False)
        if not auth:
            return
        if check_view_log(view):
            view.run_command("log_highlight")
        return


class LogHighlightRefreshThread(threading.Thread):

    def __init__(self, view):
        threading.Thread.__init__(self)
        self.view = view

    def run(self):
        global IS_WAITING
        IS_WAITING = True
        global LOGH_VIEW
        for vid in LOGH_VIEW:
            if self.view.id() == vid[0]:
                self.last_req = vid[1]
                sublime.set_timeout_async(self.refresh_wait, REFRESH_WAIT)
                break
        return

    def refresh_wait(self):
        global LOGH_VIEW
        for i, vid in enumerate(LOGH_VIEW):
            if self.view.id() == vid[0]:
                if self.last_req != vid[1]:  # more requests are comming
                    self.last_req = vid[1]
                    sublime.set_timeout_async(self.refresh_wait, REFRESH_WAIT)
                else:
                    global IS_WORKING
                    if IS_WORKING or self.view.is_loading():
                        LOGH_VIEW[i][1] = LOGH_VIEW[i][1] + 1
                        sublime.set_timeout_async(self.refresh_wait, REFRESH_WAIT)
                        break
                    else:
                        lthread = LogHighlightThread(self.view, False)
                        lthread.start()
                        IS_WAITING = False
                break
        return


class LogHighlightThread(threading.Thread):

    def __init__(self, view, is_first):
        threading.Thread.__init__(self)
        self.view     = view
        self.is_first = is_first

    def run(self):
        try:
            self.run_imp()
        except Exception:
            global IS_WORKING
            IS_WORKING = False
            disp_exept()

    def run_imp(self):
        """
        Log Highlight Main Process
        """

        global IS_WORKING
        IS_WORKING = True
        vname = self.view.file_name()
        lname = self.view.settings().get('log_name')
        panel = self.view.settings().get('panel')
        if not lname:
            return
        if panel == 'exec':
            ulink = False
            sbase = False
        else:
            ulink = get_log_property(lname, 'use_link', True)
            sropt = get_log_property(lname, 'search_base', [])
            sbase = sropt.get('enable', True)
        # to support unsaved file (like Tail)
        if not vname:
            vname = self.view.settings().get('filepath', '')
        if not vname or not os.path.isfile(vname):
            self.view.settings().set('floating', True)
        else:
            self.view.settings().set('floating', False)
        self.base_dir = ''
        self.try_search_base = False
        if self.is_first or self.view.file_name() is None:
            set_syntax_theme(self.view, lname)
            self.view.settings().set("always_prompt_for_file_reload", False)
        if self.is_first:
            global LOGH_VIEW
            if not any(self.view.id() == vid[0] for vid in LOGH_VIEW):
                LOGH_VIEW.append([self.view.id(), 0])
            winsl = sublime.windows()
            for w in winsl:
                viewl = w.views()
                for v in viewl:
                    if check_syntax(v):
                        v.settings().set('logh_lastv', False)
            global logh_lastv
            logh_lastv = self.view.id()
            self.view.settings().set('logh_lastv', True)
        else:
            if ulink and sbase:
                get_base_dir = self.view.settings().get('result_base_dir', '')
                if get_base_dir is None or get_base_dir == "":
                    self.try_search_base = True
                    self.search_base(lname, vname)
                    if self.base_dir != "":
                        self.view.settings().set('result_base_dir', self.base_dir)
                else:
                    self.base_dir = get_base_dir
            # bookmark
            self.bookmark(lname)
            IS_WORKING = False
            return
        if ulink:
            self.view.settings().set('result_file_regex', LINK_REGX_RESULT)
        if ulink and sbase:
            # to set base directory
            self.try_search_base = True
            self.search_base(lname, vname)
            # set base dir & apply 'result_file_regex'
            if self.base_dir != "":
                self.view.settings().set('result_base_dir', self.base_dir)
        # bookmark
        self.bookmark(lname)
        IS_WORKING = False
        return

    def bookmark(self, log_name):
        self.enum_severity(self.view, log_name)
        # add bookmarks
        self.goto_line = None
        self.add_bookmarks(self.view, log_name)
        # update status message
        if self.try_search_base:
            if self.search_base_success:
                fltng = self.view.settings().get('floating', True)
                sropt = get_log_property(log_name, 'search_base', [])
                sbase = sropt.get('enable', True)
                if (not fltng) and sbase:
                    sublime.status_message("Log Highlight : Found base directory - [ " + self.base_dir + " ]")
                else:
                    sublime.status_message("Log Highlight : Skipped to search base directory")
            else:
                sublime.status_message("Log Highlight : Unable to Find Base Directory !")
        bkopt = get_log_property(log_name, 'bookmark', [])
        bmkgo = bkopt.get('goto_error', True)
        if bmkgo:
            sublime.set_timeout_async(self.go_to_line, 50)
        return

    def go_to_line(self):
        # go to 1st error line
        if self.goto_line:
            self.view.show(self.goto_line)

    def get_rel_path_file(self):
        # to support unsaved file (like Tail)
        logn = self.view.file_name()
        if logn:
            text = self.view.substr(sublime.Region(0, self.view.size()))
        else:
            logn = self.view.settings().get('filepath', '')
            text = fread(logn)
        filel = re.compile(LINK_REGX_RELPATH).findall(text)
        rel_path = False
        if len(filel) > 0:
            for file_name in filel:
                if not os.path.isabs(file_name):  # use the first in relative path list
                    rel_path = True
                    break
            if rel_path:
                return file_name
            else:
                sublime.status_message("Log Highlight : There is no relative path file")
                return ""
        else:
            sublime.status_message("Log Highlight : There is no openable file path")
            return ""

    def search_base(self, log_name, view_name):
        fltng = self.view.settings().get('floating', True)
        sropt = get_log_property(log_name, 'search_base', [])
        sbase = sropt.get('enable', True)
        if fltng or (not sbase):
            self.search_base_success = True
            self.base_dir = "."
            sublime.status_message("Log Highlight : Skipped to search base directory")
            return
        file_name = self.get_rel_path_file()
        self.search_base_success = True
        self.base_dir = ''
        if file_name == '':
            return
        excludes  = sropt.get('ignore_dir', [])
        max_scan  = sropt.get('max_scan_path', MAX_SCAN_PATH)
        old_path  = ['', 0]
        _path     = os.path.dirname(view_name)
        _depth    = _path.count(os.path.sep)
        new_path  = [_path, _depth]
        scan_path = 0
        found     = False
        try:
            # check project file
            prjf = self.view.window().project_file_name()
            if isinstance(prjf, str) and prjf != "":
                pdat = self.view.window().project_data()
                pdir = os.path.dirname(prjf)
                root = pdat.get('base_dir')
                if isinstance(root, str) and root != "":
                    cpth = os.path.join(pdir, root)
                    if os.path.isfile(os.path.join(cpth, file_name)):
                        self.base_dir = root
                        found = True
            # check open folder first
            if not found:
                for root in sublime.active_window().folders():
                    if os.path.isfile(os.path.join(root, file_name)):
                        self.base_dir = root
                        found = True
                        break
            if not found:
                # scanning near the log
                for i in range(MAX_STAIR_UP_PATH):
                    for root, dirs, files in os.walk(new_path[0]):
                        dirs[:] = [d for d in dirs if (d not in excludes) and d[0] != '.']
                        if i == 0 or not root.startswith(old_path[0]):
                            sublime.status_message("Log Highlight : Searching - " + root)
                            # print (root)
                            if os.path.isfile(os.path.join(root, file_name)):
                                self.base_dir = root
                                found = True
                                break
                            else:
                                scan_path = scan_path + 1
                                if scan_path > max_scan - 1:
                                    break
                    if found or scan_path > max_scan - 1:
                        break
                    else:
                        old_path = [new_path[0], new_path[0].count(os.path.sep)]
                        _path    = os.path.dirname(old_path[0])
                        _depth   = _path.count(os.path.sep)
                        if old_path[1] == _depth or _depth < 1:  # to stop level 1 (old_path[1] == _depth == 1)
                            break
                        else:
                            new_path = [_path, _depth]
            pass
        except Exception:
            disp_exept()
        if found:
            sublime.status_message("Log Highlight : Found base directory (" + str(scan_path) + ") - [" + self.base_dir + " ]")
        else:
            sublime.status_message("Log Highlight : Fail to find (" + str(scan_path) + ") - " + file_name)
        self.search_base_success = found
        return

    def enum_severity(self, view, log_name):
        self.regions  = {}
        svt, svl = get_severity_list(log_name)
        for i, k in enumerate(svl):
            head = ''
            pat  = (svt.get(k)).get('pattern')
            for i, _pat in enumerate(pat):
                _pat[0]  = self.conv_for_regx(_pat[0])
                _pat[1]  = self.conv_for_regx(_pat[1])
                _tail    = '' if i == len(pat) - 1 else '|'
                head    += '(' + _pat[0] + ')' + _tail if _pat[1] == '' else '(' + _pat[0] + '.*?[\\r\\n])' + _tail
            region = view.find_all(head)
            self.regions[k]  = region
        return

    def add_bookmarks(self, view, log_name):
        svt, svl = get_severity_list(log_name)
        bkopt = get_log_property(log_name, 'bookmark', [])
        bmken = bkopt.get('enable', True)
        bmkgo = bkopt.get('goto_error', True)
        if not bmken:
            return
        # goto 1st error line
        if bmkgo:
            if 'error' in self.regions:
                region = self.regions['error']
                if len(region) > 0:
                    self.goto_line = region[0]
        # bookmark icon / navigation
        regions_all = []
        for i, k in enumerate(svl):
            icon = (svt.get(k)).get('icon')
            if icon:
                if icon == 'dot' or icon == 'circle' or icon == 'bookmark':
                    icon = icon
                    scpe = 'msg.' + k
                else:
                    icon = "Packages/SyntaxLog/icons/" + icon
                    scpe = 'bookmark'
                view.add_regions(k, self.regions[k], scpe, icon, sublime.HIDDEN | sublime.PERSISTENT)
            for r in self.regions[k]:
                regions_all.append(r)
        # for navigation
        view.add_regions("bookmarks", regions_all, "bookmarks", '', sublime.HIDDEN | sublime.PERSISTENT)
        return

    def conv_for_regx(self, _str):
        _str = re.sub(r'\{\{\{LINK\}\}\}', LINK_REGX_SUMMARY, _str)
        _str = re.sub(r'\{\{\{QUOTE\}\}\}', QUOTE_REGX_SUMMARY, _str)
        return _str


class LogHighlightSetAsBaseCommand(sublime_plugin.WindowCommand):

    def run(self, edit, **args):
        try:
            path = args.get('paths', [])[0]
            if os.path.isfile(path):
                path = os.path.dirname(path)
            view = sublime.active_window().active_view()
            if check_syntax(view):
                disp_msg('base directory of current log is set as : ' + path)
                self.view.settings().set('result_base_dir', path)
                global smry_view
                if smry_view is not None:
                    smry_view.settings().set('result_base_dir', path)
                # save to project
                proj = view.window().project_file_name()
                pdir = os.path.dirname(proj)
                rpth = os.path.relpath(path, pdir)
                if proj != "":
                    pdata = view.window().project_data()
                    pdata['base_dir'] = rpth
                    view.window().set_project_data(pdata)
        except Exception:
            disp_exept()
