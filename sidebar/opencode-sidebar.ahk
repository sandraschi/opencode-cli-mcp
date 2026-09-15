#Requires AutoHotkey v2.0+
#SingleInstance Force
; opencode-sidebar.ahk — old-school sidebar kludge for opencode desktop.
; Docked session list via sidebar_client.py (opencode_cli_mcp.depot, not raw SQL).
; Mutations ride the depot narrow path + backup rotation; delete is double-gated.
; Jump-to-session = command palette (Ctrl+K, Sessions category, archived excluded).
; New-session-here = opencode://new-session deep link (verified in deep-links.ts).
; Hover a row = last chat lines (previews_tsv.py). Preview pane = selectable tail.
; Filter box, star-only, cost sort + totals, auto-refresh, left/right dock.
; Right-click = rename/archive/undo/star/rate/comment (sidecar.ini, Mark column).
; Includes phase-1 guards: strip tooltip, AppsKey menu, middle-click swallow.
; Scope: OpenCode.exe only.

global STRIP_HEIGHT := 56
global WINBTN_RESERVE := 220
global SIDEBAR_W := 360
global UV_EXE := "C:\Users\sandr\.local\bin\uv.exe"
global REPO := "D:\Dev\repos\opencode-cli-mcp"
global CLIENT := REPO . "\sidebar\sidebar_client.py"
global SCRATCH := "C:\Users\sandr\AppData\Local\Temp\opencode\"
global SESS_TSV := SCRATCH . "sessions.tsv"
global PREV_TSV := SCRATCH . "previews.tsv"
global SIDECAR := SCRATCH . "sidecar.ini"
global SidebarVisible := false
global Rows := []
global Disp := []
global Previews := Map()
global LastHoverSid := ""
global SortCol := 0
global SortDir := 1
global Edge := "left"

global BG := "1A1B26"
global PANEL := "16161E"
global FG := "C0CAF5"

OnError(LogErr)
LogErr(exc, mode) {
    OutputDebug("sidebar: " . exc.Message)
    return 0
}

IsOpenCodeActive() {
    return WinActive("ahk_exe OpenCode.exe") != 0
}

MouseInStrip() {
    if (!IsOpenCodeActive()) {
        return false
    }
    try {
        CoordMode("Mouse", "Client")
        MouseGetPos(&mx, &my)
        WinGetClientPos(, , &w, , "ahk_exe OpenCode.exe")
        return my >= 0 && my <= STRIP_HEIGHT && mx >= 0 && mx <= w - WINBTN_RESERVE
    } catch {
        return false
    }
}

RunClient(args, tsv) {
    cmd := Format('cmd /c ""{1}" run --project "{2}" python "{3}" {4} > "{5}""', UV_EXE, REPO, CLIENT, args, tsv)
    RunWait(cmd, REPO . "\sidebar", "Hide")
    if (!FileExist(tsv)) {
        return ""
    }
    return FileRead(tsv)
}

Mutate(args) {
    cmd := Format('cmd /c ""{1}" run --project "{2}" python "{3}" {4}"', UV_EXE, REPO, CLIENT, args)
    RunWait(cmd, REPO . "\sidebar", "Hide")
}

MarkOf(sid) {
    star := IniRead(SIDECAR, sid, "star", "0")
    rating := IniRead(SIDECAR, sid, "rating", "")
    comment := IniRead(SIDECAR, sid, "comment", "")
    mark := (star = "1" ? "*" : "") . (rating != "" ? rating : "")
    if (comment != "") {
        mark .= (mark != "" ? " " : "") . "+"
    }
    return mark
}

RefreshSessions(lv, keepFocus := true) {
    global Rows, Disp, Previews
    keep := ""
    if (keepFocus) {
        r := lv.GetNext(0, "Focused")
        if (r && r <= Disp.Length) {
            keep := Rows[Disp[r]].id
        }
    }
    lv.Delete()
    Rows := []
    Disp := []
    Previews := Map()
    try {
        data := RunClient("list", SESS_TSV)
        if (data = "") {
            lv.Add(, "helper produced no file — check UV_EXE/HELPER paths", "", "", "", "")
        } else {
            for _, line in StrSplit(data, "`n", "`r") {
                if (line = "") {
                    continue
                }
                f := StrSplit(line, "`t")
                if (f.Length < 7) {
                    continue
                }
                cost := 0.0
                try {
                    cost := Float(f[7])
                } catch {
                }
                Rows.Push({id: f[1], title: f[2], dir: f[4], model: SubStr(f[6], 1, 30), updated: f[5], cost: cost})
            }
            prev := RunClient("previews", PREV_TSV)
            for _, line in StrSplit(prev, "`n", "`r") {
                if (line = "") {
                    continue
                }
                p := StrSplit(line, "`t", , 2)
                if (p.Length = 2) {
                    Previews[p[1]] := p[2]
                }
            }
        }
    } catch as e {
        lv.Add(, "refresh failed: " . e.Message, "", "", "", "")
    }
    ApplyView(lv, keep)
}

ApplyView(lv, keep := "") {
    global Disp
    lv.Delete()
    Disp := []
    q := StrLower(Trim(Flt.Text))
    stars := StarBox.Value
    for i, r in Rows {
        if (q != "" && !InStr(StrLower(r.title . " " . r.model . " " . r.dir), q)) {
            continue
        }
        if (stars && IniRead(SIDECAR, r.id, "star", "0") != "1") {
            continue
        }
        Disp.Push(i)
    }
    if (SortCol = 4 || SortCol = 1) {
        arr := []
        for _, i in Disp {
            arr.Push(i)
        }
        arr.Sort(SortCol = 4 ? CostCmp : TitleCmp)
        Disp := arr
    }
    total := 0.0
    for n, i in Disp {
        r := Rows[i]
        total += r.cost
        lv.Add(, r.title, r.model, r.updated, Format("{:.2f}", r.cost), MarkOf(r.id))
        if (keep != "" && r.id = keep) {
            lv.Modify(n, "Focus Select")
        }
    }
    Foot.Text := Format("{1} sessions · total {2:.2f}", Disp.Length, total)
    lv.ModifyCol(1, 140)
    lv.ModifyCol(2, 110)
    lv.ModifyCol(3, 72)
    lv.ModifyCol(4, 48)
    lv.ModifyCol(5, 45)
    UpdatePane()
}

CostCmp(a, b) {
    global SortDir, Rows
    return SortDir * Sign(Rows[a].cost - Rows[b].cost)
}

TitleCmp(a, b) {
    global SortDir, Rows
    return SortDir * StrCompare(Rows[a].title, Rows[b].title)
}

FocusedIdx() {
    r := LV.GetNext(0, "Focused")
    if (!r || r > Disp.Length) {
        return 0
    }
    return Disp[r]
}

UpdatePane() {
    i := FocusedIdx()
    if (!i) {
        Pane.Value := ""
        return
    }
    sid := Rows[i].id
    if (Previews.Has(sid) && Previews[sid] != "") {
        Pane.Value := StrReplace(Previews[sid], " // ", "`r`n")
    } else {
        Pane.Value := "(no text yet — fresh session)"
    }
}

UrlEncode(s) {
    s := StrReplace(s, "\", "%5C")
    s := StrReplace(s, " ", "%20")
    s := StrReplace(s, ":", "%3A")
    return s
}

; ---- sidebar window (dark) ----
Edge := IniRead(SIDECAR, "ui", "edge", "left")
global Bar := Gui("+AlwaysOnTop +ToolWindow +Resize", "opencode sessions")
Bar.BackColor := BG
Bar.SetFont("s9 c" . FG, "Consolas")
Bar.Add("Text", "x8 y8 w60 h22", "Filter:")
global Flt := Bar.Add("Edit", "x68 y6 w200 h24")
global StarBox := Bar.Add("Checkbox", "x274 y8 w80 h22", "* only")
global LV := Bar.Add("ListView", "x8 y36 w344 h400 -Multi", ["Title", "Model", "Updated", "Cost", "Mark"])
LV.Opt("Background" . PANEL . " c" . FG)
global Pane := Bar.Add("Edit", "x8 y444 w344 h110 +ReadOnly +Multi +VScroll", "")
Pane.Opt("Background" . PANEL . " c" . FG)
BtnRow := Bar.Add("Button", "x8 y560 w64 h26", "Refresh")
BtnJump := Bar.Add("Button", "x76 y560 w64 h26", "Jump")
BtnNew := Bar.Add("Button", "x144 y560 w64 h26", "New")
BtnHide := Bar.Add("Button", "x212 y560 w64 h26", "Hide")
BtnEdge := Bar.Add("Button", "x280 y560 w72 h26", "Edge:" . Edge)
global Foot := Bar.Add("Text", "x8 y592 w344 h20", "")

Flt.OnEvent("Change", (*) => ApplyView(LV))
StarBox.OnEvent("Click", (*) => ApplyView(LV))
BtnRow.OnEvent("Click", (*) => RefreshSessions(LV, false))
BtnJump.OnEvent("Click", (*) => JumpToSelected())
BtnNew.OnEvent("Click", (*) => NewHere())
BtnHide.OnEvent("Click", (*) => ToggleBar())
BtnEdge.OnEvent("Click", (*) => ToggleEdge())
LV.OnEvent("DoubleClick", (*) => JumpToSelected())
LV.OnEvent("ItemFocus", (*) => UpdatePane())
LV.OnEvent("ColClick", (lv, info) => ColSort(info))

ColSort(info) {
    global SortCol, SortDir
    if (SortCol = info) {
        SortDir := -SortDir
    } else {
        SortCol := info
        SortDir := (info = 4) ? -1 : 1
    }
    ApplyView(LV)
}

ToggleEdge() {
    global Edge
    Edge := (Edge = "left") ? "right" : "left"
    IniWrite(Edge, SIDECAR, "ui", "edge")
    BtnEdge.Text := "Edge:" . Edge
    GlueBar()
}

ToggleBar() {
    global SidebarVisible
    if (SidebarVisible) {
        Bar.Hide()
        ToolTip(, , , 2)
        SidebarVisible := false
    } else {
        if (!IsOpenCodeActive()) {
            WinActivate("ahk_exe OpenCode.exe")
            WinWaitActive("ahk_exe OpenCode.exe", , 3)
        }
        RefreshSessions(LV, false)
        GlueBar()
        Bar.Show("NoActivate")
        SidebarVisible := true
    }
}

GlueBar(*) {
    global SidebarVisible
    if (!SidebarVisible) {
        return
    }
    try {
        if (!WinExist("ahk_exe OpenCode.exe")) {
            Bar.Hide()
            SidebarVisible := false
            return
        }
        WinGetPos(&wx, &wy, &ww, &wh, "ahk_exe OpenCode.exe")
        h := wh - STRIP_HEIGHT - 60
        bx := (Edge = "left") ? wx + 8 : wx + ww - SIDEBAR_W - 8
        Bar.Move(bx, wy + STRIP_HEIGHT + 8, SIDEBAR_W, h)
        inner := SIDEBAR_W - 16
        Flt.Move(68, 6, inner - 150)
        StarBox.Move(inner - 76, 8)
        LV.Move(8, 36, inner, h - 36 - 176)
        Pane.Move(8, h - 176 + 8, inner, 104)
        by := h - 176 + 8 + 104 + 6
        BtnRow.Move(8, by, 64)
        BtnJump.Move(76, by, 64)
        BtnNew.Move(144, by, 64)
        BtnHide.Move(212, by, 64)
        BtnEdge.Move(280, by, inner - 280)
        Foot.Move(8, by + 30, inner)
    } catch {
    }
}
SetTimer(GlueBar, 500)

AutoRefresh(*) {
    if (SidebarVisible && IsOpenCodeActive()) {
        RefreshSessions(LV, true)
    }
}
SetTimer(AutoRefresh, 60000)

JumpToSelected() {
    i := FocusedIdx()
    if (!i) {
        return
    }
    title := Rows[i].title
    WinActivate("ahk_exe OpenCode.exe")
    WinWaitActive("ahk_exe OpenCode.exe", , 3)
    Sleep(150)
    old := A_Clipboard
    A_Clipboard := title
    Send("^k")
    Sleep(400)
    Send("^v")
    Sleep(700)
    Send("{Enter}")
    Sleep(200)
    A_Clipboard := old
}

NewHere() {
    i := FocusedIdx()
    if (!i) {
        return
    }
    Run("opencode://new-session?directory=" . UrlEncode(Rows[i].dir))
}

; ---- hit testing + hover preview ----
MouseOverLV(&sx := 0, &sy := 0) {
    if (!SidebarVisible) {
        return false
    }
    try {
        CoordMode("Mouse", "Screen")
        MouseGetPos(&sx, &sy)
        ControlGetPos(&cx, &cy, &cw, &ch, LV)
        return sx >= cx && sy >= cy && sx <= cx + cw && sy <= cy + ch
    } catch {
        return false
    }
}

RowUnderMouse() {
    if (!MouseOverLV(&sx, &sy)) {
        return 0
    }
    try {
        ControlGetPos(&cx, &cy, , , LV)
        buf := Buffer(16, 0)
        NumPut("Int", sx - cx, buf, 0)
        NumPut("Int", sy - cy, buf, 4)
        DllCall("SendMessage", "Ptr", LV.Hwnd, "UInt", 0x1012, "Ptr", 0, "Ptr", buf.Ptr)
        idx := NumGet(buf, 12, "Int") + 1
        if (idx < 1 || idx > Disp.Length) {
            return 0
        }
        return idx
    } catch {
        return 0
    }
}

HoverPreview(*) {
    global LastHoverSid
    if (!SidebarVisible) {
        return
    }
    try {
        idx := RowUnderMouse()
        if (!idx) {
            ToolTip(, , , 2)
            LastHoverSid := ""
            return
        }
        sid := Rows[Disp[idx]].id
        if (sid = LastHoverSid) {
            return
        }
        LastHoverSid := sid
        CoordMode("Mouse", "Screen")
        MouseGetPos(&sx, &sy)
        if (Previews.Has(sid) && Previews[sid] != "") {
            txt := StrReplace(SubStr(Previews[sid], 1, 1500), " // ", "`n")
            ToolTip(txt, sx + 16, sy + 16, 2)
        } else {
            ToolTip("(no text yet — fresh session)", sx + 16, sy + 16, 2)
        }
    } catch {
    }
}
SetTimer(HoverPreview, 250)

; ---- right-click context menu ----
global CtxMenu := Menu()
CtxMenu.Add("Jump to session", (*) => JumpToSelected())
CtxMenu.Add("New session here", (*) => NewHere())
CtxMenu.Add()
CtxMenu.Add("Close tab`tCtrl+W", (*) => Send("^w"))
CtxMenu.Add("Reopen closed tab`tCtrl+Shift+T", (*) => Send("^+t"))
CtxMenu.Add()
CtxMenu.Add("Rename...", (*) => CtxRename())
CtxMenu.Add("Archive", (*) => CtxArchive())
CtxMenu.Add("Delete (backup exists)...", (*) => CtxDelete())
CtxMenu.Add()
global RateMenu := Menu()
RateMenu.Add("5 - best", (*) => CtxRate("5"))
RateMenu.Add("4", (*) => CtxRate("4"))
RateMenu.Add("3", (*) => CtxRate("3"))
RateMenu.Add("2", (*) => CtxRate("2"))
RateMenu.Add("1 - worst", (*) => CtxRate("1"))
RateMenu.Add("clear", (*) => CtxRate(""))
CtxMenu.Add("Star / unstar", (*) => CtxStar())
CtxMenu.Add("Rate", RateMenu)
CtxMenu.Add("Comment...", (*) => CtxComment())
CtxMenu.Add()
CtxMenu.Add("Copy session id", (*) => CtxCopyId())

CtxSid() {
    i := FocusedIdx()
    if (!i) {
        return ""
    }
    return Rows[i].id
}

ShowCtx() {
    idx := RowUnderMouse()
    if (idx) {
        LV.Modify(idx, "Focus Select")
    }
    if (CtxSid() = "") {
        return
    }
    CoordMode("Mouse", "Screen")
    MouseGetPos(&sx, &sy)
    CtxMenu.Show(sx, sy)
}

CtxRename() {
    sid := CtxSid()
    if (sid = "") {
        return
    }
    box := InputBox("New title:", "Rename session")
    if (box.Result != "OK" || box.Value = "") {
        return
    }
    Mutate('rename "' . sid . '" "' . StrReplace(box.Value, '"', "") . '"')
    RefreshSessions(LV)
}

CtxArchive() {
    sid := CtxSid()
    if (sid = "") {
        return
    }
    Mutate("archive " . sid)
    RefreshSessions(LV)
}

CtxDelete() {
    sid := CtxSid()
    if (sid = "") {
        return
    }
    warn := "Permanently delete this session?"
    warn .= "`nTranscript, parts and todos cascade."
    warn .= "`nCovered by opencode-cli-mcp backup rotation."
    ans := MsgBox(warn, "Delete session", "YesNo Icon!")
    if (ans != "Yes") {
        return
    }
    Mutate("delete " . sid . " yes")
    RefreshSessions(LV)
}

CtxStar() {
    sid := CtxSid()
    if (sid = "") {
        return
    }
    cur := IniRead(SIDECAR, sid, "star", "0")
    IniWrite(cur = "1" ? "0" : "1", SIDECAR, sid, "star")
    RefreshSessions(LV)
}

CtxRate(v) {
    sid := CtxSid()
    if (sid = "") {
        return
    }
    IniWrite(v, SIDECAR, sid, "rating")
    RefreshSessions(LV)
}

CtxComment() {
    sid := CtxSid()
    if (sid = "") {
        return
    }
    old := IniRead(SIDECAR, sid, "comment", "")
    box := InputBox("Comment (empty clears):", "Session comment", , old)
    if (box.Result != "OK") {
        return
    }
    IniWrite(box.Value, SIDECAR, sid, "comment")
    RefreshSessions(LV)
}

CtxCopyId() {
    sid := CtxSid()
    if (sid = "") {
        return
    }
    A_Clipboard := sid
}

MouseOverLVHot() {
    sx := 0
    sy := 0
    return MouseOverLV(&sx, &sy)
}

; ---- phase-1 guards ----
PollStrip(*) {
    if (MouseInStrip()) {
        CoordMode("Mouse", "Screen")
        MouseGetPos(&sx, &sy)
        msg := "X = close TAB only — session is kept"
        msg .= "`nCtrl+Shift+T reopens · middle-click closes (guarded)"
        ToolTip(msg, sx + 16, sy + 20, 1)
    } else {
        ToolTip(, , , 1)
    }
}
SetTimer(PollStrip, 150)

global TabMenu := Menu()
TabMenu.Add("Close tab`tCtrl+W  (session kept)", (*) => Send("^w"))
TabMenu.Add("Reopen closed tab`tCtrl+Shift+T", (*) => Send("^+t"))
TabMenu.Add()
TabMenu.Add("New session`tCtrl+T", (*) => Send("^t"))
TabMenu.Add("Previous tab`tCtrl+[", (*) => Send("^["))
TabMenu.Add("Next tab`tCtrl+]", (*) => Send("^]"))
TabMenu.Add()
TabMenu.Add("Home`tCtrl+B", (*) => Send("^b"))

#HotIf IsOpenCodeActive()
AppsKey::TabMenu.Show()
^!o::ToggleBar()
#HotIf MouseOverLVHot()
RButton::ShowCtx()
#HotIf WinActive("opencode sessions")
Enter::JumpToSelected()
#HotIf
