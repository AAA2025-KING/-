(() => {
  const $ = (id) => document.getElementById(id);
  const brailleEl = $("braille");
  const contextEl = $("context");
  const backendEl = $("backend");
  const asTableEl = $("asTable");
  const resultEl = $("result");
  const metaEl = $("meta");
  const statusBox = $("statusBox");
  const btn = $("btnTranslate");
  const btnClear = $("btnClear");
  const btnPipeline = $("btnPipeline");
  const imageFile = $("imageFile");
  const tableWrap = $("tableWrap");
  const tableOut = $("tableOut");
  const mdOut = $("mdOut");
  const csvOut = $("csvOut");
  const cellPos = $("cellPos");
  const jumpRow = $("jumpRow");
  const jumpCol = $("jumpCol");
  const btnJump = $("btnJump");
  const btnSpeakCell = $("btnSpeakCell");
  const btnSpeakRow = $("btnSpeakRow");
  const btnSpeakTable = $("btnSpeakTable");
  const btnSpeakStop = $("btnSpeakStop");
  const ttsHint = $("ttsHint");
  const inputTableWrap = $("inputTableWrap");
  const inputTableOut = $("inputTableOut");
  const btnHideInputTable = $("btnHideInputTable");
  const correctZhEl = $("correctZh");
  const correctCountEl = $("correctCount");
  const correctBraillePreview = $("correctBraillePreview");
  const btnSaveCorrect = $("btnSaveCorrect");
  const btnPrepareRetrain = $("btnPrepareRetrain");
  const btnRefreshCorrectStats = $("btnRefreshCorrectStats");
  const retrainBox = $("retrainBox");

  const CELL_SEP = " | ";
  const ROW_SEP = " || ";

  // Exact grids from data/synthetic_tables t01 / 2-col demo.
  // Chip clicks MUST load these arrays directly — never parseFlat(textarea).
  const SAMPLE_TABLES = {
    t01: [
      ["⠓⠊⠼ ⠍⠊⠼⠂", "⠬ ⠒", "⠱⠥ ⠓⠾", "⠊⠼ ⠬⠄"],
      ["⠌⠦ ⠎⠧⠁", "⠼⠊⠃", "⠼⠓⠓", "⠼⠓⠑"],
      ["⠇⠊ ⠎", "⠼⠛⠓", "⠼⠊⠑", "⠼⠓⠚"],
      ["⠶⠂ ⠥", "⠼⠓⠑", "⠼⠓⠃", "⠼⠊⠚"],
    ],
    subject_mon: [
      ["⠅⠢ ⠍⠥", "⠌⠷ ⠊"],
      ["⠬ ⠒", "⠱⠥ ⠓⠾"],
    ],
  };

  function loadSampleGrid(norm, label) {
    const grid = (norm || []).map((row) => (row || []).map((c) => String(c ?? "")));
    if (!grid.length || !Array.isArray(grid[0])) return false;
    clearTable();
    clearInputTable();
    inputTableCollapsed = false;
    syncingFromInputTable = true;
    brailleEl.value = cellsToFlat(grid);
    syncingFromInputTable = false;
    if (asTableEl) asTableEl.checked = true;
    renderInputTable(grid);
    // Freeze shape: do not let a later textarea 'input' rebuild via parseFlat.
    inputCells = grid.map((row) => row.slice());
    metaEl.textContent = "已填入样例「" + label + "」" + grid.length + "×" + grid[0].length + "，可点翻译。";
    return true;
  }

  /** @type {string[][]} */
  let tableCells = [];
  /** @type {string[][]} */
  let inputCells = [];
  let selR = -1;
  let selC = -1;
  let syncingFromInputTable = false;
  let inputTableCollapsed = false;
  /** @type {SpeechSynthesisVoice | null} */
  let zhVoice = null;

  const ttsSupported = typeof window.speechSynthesis !== "undefined";

  function setStatus(text, kind) {
    statusBox.textContent = text;
    const base = statusBox.classList.contains("status-inline")
      ? "status status-inline"
      : "status";
    statusBox.className = base + (kind ? " " + kind : "");
  }

  function isFlatTable(text) {
    const s = text || "";
    if (s.includes(ROW_SEP) || s.includes("||")) return true;
    let count = 0;
    let idx = 0;
    while ((idx = s.indexOf(CELL_SEP, idx)) !== -1) {
      count++;
      idx += CELL_SEP.length;
    }
    if (count >= 2) return true;
    const pipeCount = (s.match(/\|/g) || []).length;
    if (pipeCount >= 2) return true;
    // pasted multi-line tables: newline + at least one pipe
    if (s.includes("\n") && pipeCount >= 1) return true;
    return false;
  }

  function sanitizeCell(text) {
    return String(text ?? "")
      .replace(/<\/?\s*tool_?response\s*>/gi, "")
      .replace(/<\/?\s*tool_?calls?\s*>/gi, "")
      .replace(/<\/?\s*quote\b[^>]*>/gi, "")
      .replace(/<quote\b[^>]*>?/gi, "")
      .replace(/<\|\/?[^|>]+\|>/g, "")
      .replace(/[ \t]{2,}/g, " ")
      .trim();
  }

  function gridScore(cells) {
    if (!cells || !cells.length) return 0;
    let cols = 0;
    for (const row of cells) cols = Math.max(cols, (row || []).length);
    const headerW = (cells[0] || []).length;
    let rect = 0;
    for (const row of cells) {
      if ((row || []).length === headerW) rect += 10;
    }
    return cells.length * 100 + cols + rect;
  }

  function colMatchScore(n, target) {
    if (!target || target <= 0) return n;
    if (n === target) return 10000 + n;
    if (n < target) return 100 * n;
    return 100 * target - 10 * (n - target);
  }

  /** School/schedule tokens for splitting jammed Chinese like "语文数学". */
  const CJK_TOKENS = [
    "信息技术",
    "及格率",
    "语文",
    "数学",
    "英语",
    "物理",
    "化学",
    "生物",
    "历史",
    "地理",
    "政治",
    "体育",
    "音乐",
    "美术",
    "品德",
    "科学",
    "综合",
    "科目",
    "姓名",
    "序号",
    "分数",
    "成绩",
    "平均",
    "最高",
    "最低",
    "周一",
    "周二",
    "周三",
    "周四",
    "周五",
    "周六",
    "周日",
    "星期",
    "节次",
    "时间",
    "课程",
    "教室",
    "商品",
    "数量",
    "单价",
    "金额",
    "区域",
    "总位",
    "占用",
    "空闲",
  ].sort((a, b) => b.length - a.length);

  /** Greedy-split jammed CJK compounds: 语文数学 → ["语文","数学"]. */
  function splitJammedCjk(text, targetCols) {
    const s = String(text || "").trim();
    if (!s) return [""];
    if (s.includes("|") || /\s/.test(s)) return [s];
    if (/[\u2800-\u283F]/.test(s)) return [s];
    if (!/^[\u4e00-\u9fff\d]+$/.test(s)) return [s];
    const parts = [];
    let rest = s;
    const dm = rest.match(/^(\d+)([\u4e00-\u9fff].*)$/);
    if (dm) {
      parts.push(dm[1]);
      rest = dm[2];
    }
    let i = 0;
    while (i < rest.length) {
      if (targetCols && parts.length >= targetCols) {
        parts[parts.length - 1] = parts[parts.length - 1] + rest.slice(i);
        break;
      }
      let matched = false;
      for (const tok of CJK_TOKENS) {
        if (rest.startsWith(tok, i)) {
          parts.push(tok);
          i += tok.length;
          matched = true;
          break;
        }
      }
      if (matched) continue;
      if (
        i + 2 <= rest.length &&
        /^[\u4e00-\u9fff]{2}/.test(rest.slice(i))
      ) {
        parts.push(rest.slice(i, i + 2));
        i += 2;
        continue;
      }
      if (parts.length) parts[parts.length - 1] += rest.slice(i);
      else parts.push(rest.slice(i));
      break;
    }
    if (targetCols && targetCols > 0 && parts.length > targetCols) {
      return parts
        .slice(0, targetCols - 1)
        .concat([parts.slice(targetCols - 1).join("")]);
    }
    return parts.length > 1 ? parts : [s];
  }

  /** Chinese/ASCII jammed data (spaces, digit+CJK, or lexicon compounds). */
  function looksLikeJammedZhData(s) {
    const t = String(s || "");
    if (!t || /[\u2800-\u283F]/.test(t)) return false;
    if (t.includes("|")) return false;
    if (/\s/.test(t)) return true;
    // e.g. "1语文" — leading digits glued to CJK with no space
    if (/^\d+[\u4e00-\u9fff]/.test(t)) return true;
    // e.g. "语文数学" — no spaces but lexicon-splittable
    if (/^[\u4e00-\u9fff]{4,}$/.test(t) && splitJammedCjk(t).length > 1) {
      return true;
    }
    return false;
  }

  /**
   * Tokenize a Chinese/ASCII data blob:
   * - whitespace → tokens
   * - leading digits glued to CJK: "1语文" → ["1","语文"]
   * - jammed compounds: "语文数学" → ["语文","数学"]
   * Leaves braille untouched.
   */
  function tokenizeZhDataBlob(text, targetCols) {
    const s = String(text || "").trim();
    if (!s) return [""];
    if (/[\u2800-\u283F]/.test(s)) return [s];
    if (/\s/.test(s) || /^\d+[\u4e00-\u9fff]/.test(s)) {
      const rough = s.split(/\s+/).filter((c) => c !== "");
      const out = [];
      for (const tok of rough) {
        const m = tok.match(/^(\d+)([\u4e00-\u9fff].*)$/);
        if (m) {
          out.push(m[1]);
          const rest = splitJammedCjk(m[2], targetCols);
          for (const x of rest) out.push(x);
        } else if (/^[\u4e00-\u9fff]{4,}$/.test(tok)) {
          const parts = splitJammedCjk(tok, targetCols);
          for (const x of parts) out.push(x);
        } else {
          out.push(tok);
        }
      }
      return out.length ? out : [s];
    }
    if (/^[\u4e00-\u9fff\d]+$/.test(s)) {
      const parts = splitJammedCjk(s, targetCols);
      if (parts.length > 1) return parts;
    }
    return [s];
  }

  /** Expand jammed Chinese tokens inside an already pipe-split cell list.
   *  Trailing empty pads are dropped before expand, then caller normalizes width.
   *  So ["1语文","数学","","…"] → ["1","语文","数学"] (not length-8 with pads).
   */
  function expandZhTokensInCells(cells, targetCols) {
    const raw = (cells || []).map((c) => String(c || ""));
    // Drop trailing empties so expanding "1语文" does not fight pad length==width.
    let end = raw.length;
    while (end > 0 && !String(raw[end - 1] || "").trim()) end--;
    const core = raw.slice(0, end);
    const out = [];
    let didExpand = false;
    for (const c of core) {
      const t = String(c || "").trim();
      if (!t) {
        out.push("");
        continue;
      }
      if (/[\u2800-\u283F]/.test(t) || t.includes("|")) {
        out.push(t);
        continue;
      }
      if (looksLikeJammedZhData(t)) {
        const toks = tokenizeZhDataBlob(t, targetCols);
        if (toks.length > 1) {
          for (const x of toks) out.push(x);
          didExpand = true;
          continue;
        }
      }
      out.push(t);
    }
    if (!didExpand && out.length === core.length) {
      return cells;
    }
    // Prefer expansion when it moves closer to targetCols (or any expand without target).
    if (
      targetCols &&
      colMatchScore(out.length, targetCols) <
        colMatchScore(core.length, targetCols) &&
      colMatchScore(out.length, targetCols) <
        colMatchScore((cells || []).length, targetCols)
    ) {
      return cells;
    }
    return out;
  }


  function stripCellEdgePipes(cell) {
    let t = String(cell || "").trim();
    if (t.startsWith("|")) t = t.replace(/^\|+/, "").trim();
    if (t.endsWith("|")) t = t.replace(/\|+$/, "").trim();
    return t;
  }

  /** Drop empty leading/trailing cells from markdown ``| a | b |`` / ``|a|b|``. */
  function trimMarkdownPipeBorders(cells) {
    if (!cells || !cells.length) return cells;
    let out = cells.map(stripCellEdgePipes);
    while (out.length && out[0] === "") out.shift();
    while (out.length && out[out.length - 1] === "") out.pop();
    return out.length ? out : [""];
  }

  function isMarkdownSeparatorRow(cells) {
    if (!cells || !cells.length) return false;
    let saw = false;
    for (const c of cells) {
      let s = String(c || "").trim().replace(/^\|+|\|+$/g, "").trim();
      if (!s) continue;
      saw = true;
      if (!/^:?-{3,}:?$/.test(s)) return false;
    }
    return saw;
  }

  function splitRowPart(part, targetCols) {
    const p = String(part || "").trim();
    if (!p) return [""];
    const hasPipe = p.includes("|");
    let pipeCells;
    if (p.includes(CELL_SEP)) {
      pipeCells = p.split(CELL_SEP).map((c) => c.trim());
    } else if (hasPipe) {
      pipeCells = p.split("|").map((c) => c.trim());
    } else {
      pipeCells = [p];
    }
    if (hasPipe) {
      pipeCells = trimMarkdownPipeBorders(pipeCells);
    }
    // Keep pipe splits by default — braille cells often contain internal spaces.
    if (hasPipe) {
      if (!targetCols || pipeCells.length >= targetCols) {
        // Still expand digit+CJK inside each pipe cell when under/equal width.
        const expanded = expandZhTokensInCells(pipeCells, targetCols);
        if (
          !targetCols ||
          colMatchScore(expanded.length, targetCols) >=
            colMatchScore(pipeCells.length, targetCols)
        ) {
          return expanded;
        }
        return pipeCells;
      }
      const expanded = expandZhTokensInCells(pipeCells, targetCols);
      if (
        colMatchScore(expanded.length, targetCols) >
        colMatchScore(pipeCells.length, targetCols)
      ) {
        return expanded;
      }
      if (pipeCells.length === 1 && looksLikeJammedZhData(pipeCells[0] || "")) {
        const wsOne = tokenizeZhDataBlob(pipeCells[0], targetCols);
        if (
          wsOne.length &&
          colMatchScore(wsOne.length, targetCols) >
            colMatchScore(pipeCells.length, targetCols)
        ) {
          return wsOne;
        }
      }
      return pipeCells;
    }
    // No pipes: whitespace + digit/CJK jam split for Chinese/ASCII data rows.
    if (looksLikeJammedZhData(p)) {
      const toks = tokenizeZhDataBlob(p, targetCols);
      if (toks.length > 1) {
        if (
          !targetCols ||
          colMatchScore(toks.length, targetCols) >
            colMatchScore(pipeCells.length, targetCols)
        ) {
          return toks;
        }
      }
    }
    return pipeCells;
  }

  function normalizeGrid(cells, width) {
    if (!cells || !cells.length) return [];
    const rows = cells.map((row) => (row || []).map((c) => sanitizeCell(c)));
    let w = width;
    if (!w || w <= 0) {
      w = rows[0].length || Math.max(...rows.map((r) => r.length), 0);
    }
    if (!w || w <= 0) return rows;
    return rows.map((row) => {
      if (row.length < w) return row.concat(Array(w - row.length).fill(""));
      return row.slice(0, w);
    });
  }

  /** Split any cell whose text contains `|` into multiple cells on that row. */
  function expandPipeInRow(row) {
    const raw = row || [];
    const nonempty = [];
    for (let j = 0; j < raw.length; j++) {
      const s = sanitizeCell(raw[j]);
      if (s) nonempty.push([j, s]);
    }
    // Common bug: one pipe-joined header blob + empty pads from align-to-width.
    if (nonempty.length === 1 && nonempty[0][1].includes("|")) {
      const blob = nonempty[0][1];
      const parts = blob.includes(CELL_SEP)
        ? blob.split(CELL_SEP)
        : blob.split("|");
      return parts.map((c) => sanitizeCell(c));
    }
    // One jammed Chinese/ASCII blob + empty pads → collapse so later split can run.
    if (
      nonempty.length === 1 &&
      looksLikeJammedZhData(nonempty[0][1] || "") &&
      raw.length > 1
    ) {
      return [nonempty[0][1]];
    }
    const out = [];
    for (const cell of raw) {
      const s = sanitizeCell(cell);
      if (s.includes("|")) {
        const parts = s.includes(CELL_SEP) ? s.split(CELL_SEP) : s.split("|");
        for (const p of parts) out.push(sanitizeCell(p));
      } else if (looksLikeJammedZhData(s)) {
        const toks = tokenizeZhDataBlob(s);
        if (toks.length > 1) {
          for (const t of toks) out.push(sanitizeCell(t));
        } else {
          out.push(s);
        }
      } else {
        out.push(s);
      }
    }
    return out;
  }

  /**
   * Normalize pass: expand pipe-joined cells, then whitespace-split short
   * data rows so the grid matches header width (e.g. 7 columns).
   */
  function expandPipeInGrid(cells, preferWidth) {
    if (!cells || !cells.length) return [];
    let rows = cells.map((row) => expandPipeInRow(row));
    let width =
      (preferWidth && preferWidth > 0 ? preferWidth : 0) ||
      Math.max(...rows.map((r) => r.length), 0);
    // Header row with pipes establishes width when preferWidth missing/short.
    if (rows[0] && rows[0].length > width) width = rows[0].length;
    for (let i = 0; i < rows.length; i++) {
      let row = rows[i];
      if (row.length >= width && width > 0) {
        rows[i] = row.slice(0, width);
        continue;
      }
      if (row.length === 1 && looksLikeJammedZhData(row[0] || "")) {
        const ws = splitRowPart(row[0], width || undefined);
        if (
          !width ||
          colMatchScore(ws.length, width) > colMatchScore(row.length, width)
        ) {
          row = ws.map((c) => sanitizeCell(c));
          if (row.length > width) width = row.length;
        }
      } else if (width && row.length < width) {
        // e.g. ["1语文","数学","","..."] → ["1","语文","数学",...]
        const expanded = expandZhTokensInCells(row, width);
        if (
          colMatchScore(expanded.length, width) >
          colMatchScore(row.length, width)
        ) {
          row = expanded.map((c) => sanitizeCell(c));
          if (row.length > width) width = row.length;
        }
      }
      rows[i] = row;
    }
    width = Math.max(width, ...rows.map((r) => r.length), 0);
    return normalizeGrid(rows, width);
  }

  function parseFlat(text, targetCols) {
    let raw = (text || "").trim();
    if (!raw) return [];
    raw = raw.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    // Normalize row separators: || without spaces, or newlines as rows
    if (!raw.includes(ROW_SEP)) {
      if (raw.includes("||")) {
        raw = raw.split("||").map((p) => p.trim()).join(ROW_SEP);
      } else if (raw.includes("\n")) {
        raw = raw
          .split("\n")
          .map((p) => p.trim())
          .filter((p) => p !== "")
          .join(ROW_SEP);
      }
    }
    const rows = [];
    for (const rowPart of raw.split(ROW_SEP)) {
      const part = rowPart.trim();
      const rowTarget = targetCols || (rows.length ? rows[0].length : undefined);
      let cells = splitRowPart(part, rowTarget);
      if (cells.length === 1 && cells[0] === "" && !rows.length) continue;
      if (isMarkdownSeparatorRow(cells)) continue;
      rows.push(cells.map(sanitizeCell));
    }
    if (!rows.length) return [];
    const width = targetCols && targetCols > 0 ? targetCols : rows[0].length;
    if (width > 1) {
      const fixed = [rows[0]];
      for (let i = 1; i < rows.length; i++) {
        const row = rows[i];
        if (row.length >= width) {
          fixed.push(row.slice(0, width));
          continue;
        }
        if (row.length === 1 && /\s/.test(row[0] || "")) {
          const ws = splitRowPart(row[0], width);
          if (colMatchScore(ws.length, width) > colMatchScore(row.length, width)) {
            fixed.push(ws);
            continue;
          }
        }
        fixed.push(row);
      }
      return normalizeGrid(fixed, width);
    }
    return normalizeGrid(rows, width);
  }

  function cellsToMarkdown(cells) {
    if (!cells.length) return "";
    const width = Math.max(...cells.map((r) => r.length));
    const norm = cells.map((r) => {
      const row = r.slice();
      while (row.length < width) row.push("");
      return row;
    });
    const lines = [
      "| " + norm[0].join(" | ") + " |",
      "| " + norm[0].map(() => "---").join(" | ") + " |",
    ];
    for (let i = 1; i < norm.length; i++) {
      lines.push("| " + norm[i].join(" | ") + " |");
    }
    return lines.join("\n");
  }

  function cellsToCsvClient(cells) {
    return cells
      .map((row) =>
        row
          .map((c) => {
            const s = String(c ?? "");
            return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
          })
          .join(",")
      )
      .join("\n");
  }

  function cellsToFlat(cells) {
    return cells.map((row) => row.map((c) => String(c ?? "")).join(CELL_SEP)).join(ROW_SEP);
  }

  function clearInputTable() {
    inputCells = [];
    if (inputTableOut) inputTableOut.innerHTML = "";
    if (inputTableWrap) inputTableWrap.classList.add("hidden");
  }

  function renderInputTable(cells) {
    if (!inputTableOut || !inputTableWrap) return;
    inputCells = cells.map((row) => row.map((c) => String(c ?? "")));
    if (!inputCells.length || inputTableCollapsed) {
      if (!inputCells.length) inputTableWrap.classList.add("hidden");
      return;
    }
    const parts = ['<table class="cbt-table cbt-input-table"><tbody>'];
    inputCells.forEach((row, i) => {
      parts.push("<tr>");
      row.forEach((c, j) => {
        const esc = String(c)
          .replace(/&/g, "&amp;")
          .replace(/"/g, "&quot;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;");
        parts.push(
          "<td><input class=\"cbt-input-cell\" data-r=\"" +
            i +
            "\" data-c=\"" +
            j +
            "\" type=\"text\" value=\"" +
            esc +
            "\" spellcheck=\"false\" /></td>"
        );
      });
      parts.push("</tr>");
    });
    parts.push("</tbody></table>");
    inputTableOut.innerHTML = parts.join("");
    inputTableWrap.classList.remove("hidden");

    inputTableOut.querySelectorAll(".cbt-input-cell").forEach((inp) => {
      inp.addEventListener("input", () => {
        const r = Number(inp.getAttribute("data-r"));
        const c = Number(inp.getAttribute("data-c"));
        if (!inputCells[r]) return;
        inputCells[r][c] = inp.value;
        syncingFromInputTable = true;
        brailleEl.value = cellsToFlat(inputCells);
        syncingFromInputTable = false;
        if (asTableEl) asTableEl.checked = true;
      });
    });
  }

  function refreshInputTableFromTextarea() {
    if (syncingFromInputTable) return;
    const text = brailleEl.value || "";
    if (!isFlatTable(text)) {
      clearInputTable();
      return;
    }
    if (asTableEl) asTableEl.checked = true;
    inputTableCollapsed = false;
    const cells = parseFlat(text);
    // Avoid rebuild if same shape+content (keeps focus while typing in textarea)
    const flatNow = cellsToFlat(cells);
    const flatPrev = cellsToFlat(inputCells);
    if (flatNow === flatPrev && inputTableWrap && !inputTableWrap.classList.contains("hidden")) {
      return;
    }
    renderInputTable(cells);
  }

  function clearTable() {
    stopSpeak();
    tableWrap.classList.add("hidden");
    tableOut.innerHTML = "";
    mdOut.value = "";
    csvOut.value = "";
    tableCells = [];
    selR = -1;
    selC = -1;
    if (cellPos) cellPos.textContent = "点击或用方向键选择单元格";
  }

  function cellText(r, c) {
    if (!tableCells[r] || tableCells[r][c] == null) return "";
    return String(tableCells[r][c]);
  }

  function brailleCellText(r, c) {
    if (!inputCells[r] || inputCells[r][c] == null) return "";
    return String(inputCells[r][c]);
  }

  function syncCorrectPanel() {
    if (!correctBraillePreview) return;
    if (selR < 0 || selC < 0) {
      correctBraillePreview.innerHTML =
        "选中单元格后可改正汉字并保存为训练样本。";
      if (correctZhEl && document.activeElement !== correctZhEl) {
        correctZhEl.value = "";
      }
      return;
    }
    const br = brailleCellText(selR, selC);
    const pred = cellText(selR, selC);
    correctBraillePreview.innerHTML =
      "第 " +
      (selR + 1) +
      " 行 " +
      (selC + 1) +
      " 列 · 盲文 <code>" +
      escapeHtml(br || "（无）") +
      "</code> · 原译 <code>" +
      escapeHtml(pred || "（空）") +
      "</code>";
    if (correctZhEl && document.activeElement !== correctZhEl) {
      correctZhEl.value = pred || "";
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function updateCellPos() {
    if (!cellPos) return;
    if (selR < 0 || selC < 0) {
      cellPos.textContent = "点击或用方向键选择单元格";
      syncCorrectPanel();
      return;
    }
    const text = cellText(selR, selC);
    cellPos.textContent =
      "第 " + (selR + 1) + " 行，第 " + (selC + 1) + " 列 · 内容：" + (text || "（空）");
    if (jumpRow) jumpRow.value = String(selR + 1);
    if (jumpCol) jumpCol.value = String(selC + 1);
    syncCorrectPanel();
  }

  function clearHighlights() {
    tableOut.querySelectorAll(".cbt-selected, .cbt-row-hl, .cbt-col-hl").forEach((el) => {
      el.classList.remove("cbt-selected", "cbt-row-hl", "cbt-col-hl");
    });
  }

  function selectCell(r, c, { focus = true } = {}) {
    if (!tableCells.length) return;
    const maxR = tableCells.length - 1;
    if (r < 0 || r > maxR) return;
    const maxC = (tableCells[r] || []).length - 1;
    if (maxC < 0 || c < 0 || c > maxC) return;
    selR = r;
    selC = c;
    clearHighlights();
    tableOut.querySelectorAll(".cbt-cell").forEach((el) => {
      const er = Number(el.getAttribute("data-r"));
      const ec = Number(el.getAttribute("data-c"));
      if (er === r) el.classList.add("cbt-row-hl");
      if (ec === c) el.classList.add("cbt-col-hl");
      if (er === r && ec === c) {
        el.classList.add("cbt-selected");
        if (focus) el.focus();
      }
    });
    updateCellPos();
  }

  function bindTableEvents() {
    const table = tableOut.querySelector("table");
    if (!table) return;
    table.setAttribute("role", "grid");
    tableOut.querySelectorAll(".cbt-cell").forEach((el) => {
      el.addEventListener("click", () => {
        selectCell(Number(el.getAttribute("data-r")), Number(el.getAttribute("data-c")));
      });
      el.addEventListener("keydown", (e) => {
        const r = Number(el.getAttribute("data-r"));
        const c = Number(el.getAttribute("data-c"));
        const rowLen = (tableCells[r] || []).length;
        let nr = r;
        let nc = c;
        if (e.key === "ArrowUp") {
          e.preventDefault();
          nr = Math.max(0, r - 1);
          nc = Math.min(c, (tableCells[nr] || []).length - 1);
        } else if (e.key === "ArrowDown") {
          e.preventDefault();
          nr = Math.min(tableCells.length - 1, r + 1);
          nc = Math.min(c, (tableCells[nr] || []).length - 1);
        } else if (e.key === "ArrowLeft") {
          e.preventDefault();
          nc = Math.max(0, c - 1);
        } else if (e.key === "ArrowRight") {
          e.preventDefault();
          nc = Math.min(rowLen - 1, c + 1);
        } else if (e.key === "Home") {
          e.preventDefault();
          nc = 0;
        } else if (e.key === "End") {
          e.preventDefault();
          nc = rowLen - 1;
        } else if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          selectCell(r, c);
          return;
        } else {
          return;
        }
        selectCell(nr, nc);
      });
    });
  }

  function ensureCellAttrsFromCells() {
    if (!tableCells.length) return;
    const parts = ['<table class="cbt-table">'];
    tableCells.forEach((row, i) => {
      const tag = i === 0 ? "th" : "td";
      const cellsHtml = row
        .map((c, j) => {
          const esc = String(c)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
          return (
            "<" +
            tag +
            ' class="cbt-cell" data-r="' +
            i +
            '" data-c="' +
            j +
            '" tabindex="0">' +
            esc +
            "</" +
            tag +
            ">"
          );
        })
        .join("");
      parts.push("<tr>" + cellsHtml + "</tr>");
    });
    parts.push("</table>");
    tableOut.innerHTML = parts.join("\n");
  }

  function shapeKey(cells) {
    if (!cells || !cells.length) return "";
    return cells.map((r) => (r || []).length).join(",");
  }

  /** Force grid to the exact rows/cols of the input preview (pad/truncate only).
   *  Never expand pipes / lexicon-split / whitespace-resplit — that breaks shape.
   */
  function alignToInputShape(sourceCells, shapeCells) {
    if (!shapeCells || !shapeCells.length) {
      return expandPipeInGrid(sourceCells || []);
    }
    const out = [];
    for (let i = 0; i < shapeCells.length; i++) {
      const shapeRow = shapeCells[i] || [];
      const srcRow = (sourceCells && sourceCells[i]) || [];
      const row = [];
      for (let j = 0; j < shapeRow.length; j++) {
        row.push(srcRow[j] !== undefined ? sanitizeCell(srcRow[j]) : "");
      }
      out.push(row);
    }
    return out;
  }

  function repairShortRows(cells, targetWidth) {
    if (!cells || !cells.length) return cells;
    const width = targetWidth || (cells[0] || []).length;
    if (!width) return cells;
    const out = [];
    for (let i = 0; i < cells.length; i++) {
      let row = (cells[i] || []).map((c) => sanitizeCell(c));
      while (row.length < width) row.push("");
      const nonempty = [];
      for (let j = 0; j < row.length; j++) {
        if (String(row[j] || "").trim()) nonempty.push([j, row[j]]);
      }
      let blobIdx = null;
      let blobText = "";
      if (nonempty.length === 1 && looksLikeJammedZhData(nonempty[0][1] || "")) {
        blobIdx = nonempty[0][0];
        blobText = nonempty[0][1];
      } else if (row.length === 1 && looksLikeJammedZhData(row[0] || "")) {
        blobIdx = 0;
        blobText = row[0];
      }
      if (blobIdx !== null) {
        let ws = splitRowPart(blobText, width);
        if (ws.length <= 1 && looksLikeJammedZhData(blobText)) {
          const cjk = splitJammedCjk(blobText, width);
          if (colMatchScore(cjk.length, width) > colMatchScore(ws.length, width)) {
            ws = cjk;
          }
        }
        if (
          colMatchScore(ws.length, width) >
          colMatchScore(nonempty.length || row.length, width)
        ) {
          const newRow = row.slice();
          while (newRow.length < width) newRow.push("");
          for (let k = blobIdx; k < Math.min(width, blobIdx + Math.max(ws.length, 1)); k++) {
            newRow[k] = "";
          }
          for (let k = 0; k < ws.length; k++) {
            const pos = blobIdx + k;
            if (pos >= width) break;
            newRow[pos] = sanitizeCell(ws[k]);
          }
          row = newRow;
        }
      } else {
        const expanded = expandZhTokensInCells(row, width);
        if (
          colMatchScore(expanded.length, width) >
          colMatchScore(row.length, width)
        ) {
          row = expanded;
        }
      }
      out.push(row);
    }
    return normalizeGrid(out, width);
  }

  function showTable(table, textFallback) {
    // Restore grid priority (strict):
    // 1) If input preview grid exists → ALWAYS mirror its exact shape.
    //    Each cell = that cell's translation only. NO pipe expand, NO
    //    lexicon/whitespace re-split (those heuristics break 2x2 / NxM).
    // 2) Else prefer API cells; fallback parse(汉字) only when API empty/worse
    //    (heuristics allowed only when input shape is unknown).
    stopSpeak();
    let apiCells = [];
    if (table && Array.isArray(table.cells) && table.cells.length) {
      apiCells = table.cells.map((row) =>
        Array.isArray(row) ? row.map((c) => sanitizeCell(c)) : []
      );
    }
    const text =
      textFallback ||
      (table && table.flat_zh) ||
      (resultEl && resultEl.value) ||
      "";
    const preferWidth =
      (inputCells.length && (inputCells[0] || []).length) ||
      (apiCells.length && (apiCells[0] || []).length) ||
      undefined;
    const fromText = parseFlat(text, preferWidth);
    let cells = [];

    if (inputCells.length) {
      const src = apiCells.length ? apiCells : fromText;
      if (!src.length) {
        clearTable();
        return;
      }
      // Strict 1:1 with input preview — no expand / repair.
      cells = alignToInputShape(src, inputCells);
    } else if (apiCells.length) {
      // Input shape unknown: heuristics OK to recover pipe/whitespace tables.
      cells = expandPipeInGrid(apiCells);
      cells = repairShortRows(cells, (cells[0] || []).length);
      if (fromText.length && gridScore(fromText) > gridScore(cells)) {
        cells = expandPipeInGrid(fromText);
        cells = repairShortRows(cells, (cells[0] || []).length);
      }
    } else if (fromText.length) {
      cells = expandPipeInGrid(fromText);
      cells = repairShortRows(cells, (cells[0] || []).length);
    } else {
      clearTable();
      return;
    }

    // Keep 汉字结果 identical to the restored grid (same rows/cols & separators).
    if (resultEl && cells.length) {
      resultEl.value = cellsToFlat(cells);
    }

    tableWrap.classList.remove("hidden");
    tableCells = cells;
    // Always rebuild HTML from cells (never trust raw html with leaked tags).
    tableOut.innerHTML = "";
    ensureCellAttrsFromCells();
    mdOut.value = cellsToMarkdown(cells);
    csvOut.value = cellsToCsvClient(cells);
    bindTableEvents();
    selR = -1;
    selC = -1;
    updateCellPos();
    if (tableCells.length && (tableCells[0] || []).length) {
      selectCell(0, 0, { focus: false });
    }
  }

  function pickZhVoice() {
    if (!ttsSupported) return null;
    const voices = window.speechSynthesis.getVoices() || [];
    const prefer =
      voices.find((v) => /zh-CN/i.test(v.lang)) ||
      voices.find((v) => /zh[-_]?Hans/i.test(v.lang)) ||
      voices.find((v) => /^zh/i.test(v.lang)) ||
      voices.find((v) => /Chinese|中文|普通话|国语/i.test(v.name)) ||
      null;
    zhVoice = prefer;
    return prefer;
  }

  if (ttsSupported) {
    pickZhVoice();
    window.speechSynthesis.onvoiceschanged = () => pickZhVoice();
    if (ttsHint) ttsHint.classList.add("hidden");
  } else {
    if (ttsHint) ttsHint.classList.remove("hidden");
    [btnSpeakCell, btnSpeakRow, btnSpeakTable, btnSpeakStop].forEach((b) => {
      if (b) b.disabled = true;
    });
  }

  function stopSpeak() {
    if (ttsSupported) {
      try {
        window.speechSynthesis.cancel();
      } catch (_) {}
    }
  }

  function speakText(text, { onend } = {}) {
    if (!ttsSupported) return;
    const u = new SpeechSynthesisUtterance(text || "");
    u.lang = "zh-CN";
    u.rate = 0.95;
    const voice = zhVoice || pickZhVoice();
    if (voice) u.voice = voice;
    if (onend) u.onend = onend;
    window.speechSynthesis.speak(u);
  }

  function speakQueue(parts) {
    if (!ttsSupported || !parts.length) return;
    stopSpeak();
    let i = 0;
    const next = () => {
      if (i >= parts.length) return;
      const chunk = parts[i++];
      speakText(chunk, { onend: next });
    };
    next();
  }

  function speakCell() {
    if (selR < 0 || selC < 0) {
      metaEl.textContent = "请先选择一个单元格。";
      return;
    }
    const text = cellText(selR, selC) || "空";
    const announce =
      "第" + (selR + 1) + "行第" + (selC + 1) + "列，" + text;
    stopSpeak();
    speakText(announce);
  }

  function speakRow() {
    if (selR < 0) {
      metaEl.textContent = "请先选择一行中的单元格。";
      return;
    }
    const row = tableCells[selR] || [];
    const parts = row.map((c) => {
      const t = String(c || "").trim() || "空";
      return t;
    });
    speakQueue(parts.map((t, i) => (i === 0 ? t : "，" + t)));
  }

  function speakTable() {
    if (!tableCells.length) {
      metaEl.textContent = "没有可朗读的表格。";
      return;
    }
    const parts = [];
    tableCells.forEach((row, r) => {
      row.forEach((c, j) => {
        const t = String(c || "").trim() || "空";
        if (j === 0 && r > 0) {
          parts.push("。第" + (r + 1) + "行，" + t);
        } else if (j === 0) {
          parts.push("第" + (r + 1) + "行，" + t);
        } else {
          parts.push("，" + t);
        }
      });
    });
    speakQueue(parts);
  }

  function doJump() {
    const r = parseInt(jumpRow && jumpRow.value, 10);
    const c = parseInt(jumpCol && jumpCol.value, 10);
    if (!Number.isFinite(r) || !Number.isFinite(c) || r < 1 || c < 1) {
      metaEl.textContent = "请输入有效的行号与列号（从 1 开始）。";
      return;
    }
    selectCell(r - 1, c - 1);
  }


  async function refreshCorrectStats() {
    try {
      const res = await fetch("/v1/corrections/stats", { cache: "no-store" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const s = await res.json();
      const n = s.user_corrections || 0;
      if (correctCountEl) {
        correctCountEl.textContent =
          "纠错 " + n + " 条" +
          (s.train_tables_with_errors
            ? " · 合并集 " + s.train_tables_with_errors
            : "");
      }
      return s;
    } catch (err) {
      if (correctCountEl) correctCountEl.textContent = "纠错计数不可用";
      return null;
    }
  }

  function showRetrainBox(text, kind) {
    if (!retrainBox) return;
    retrainBox.classList.remove("hidden", "ok", "warn", "err");
    if (kind) retrainBox.classList.add(kind);
    retrainBox.textContent = text;
  }

  async function doSaveCorrect() {
    if (selR < 0 || selC < 0) {
      metaEl.textContent = "请先选择要纠正的单元格。";
      return;
    }
    const br = (brailleCellText(selR, selC) || "").trim();
    const pred = cellText(selR, selC);
    const zh = ((correctZhEl && correctZhEl.value) || "").trim();
    if (!br) {
      metaEl.textContent = "该格没有对应盲文（请用输入表格或带 | 的盲文翻译）。";
      return;
    }
    if (!zh) {
      metaEl.textContent = "请填写正确汉字。";
      if (correctZhEl) correctZhEl.focus();
      return;
    }
    if (zh === String(pred || "").trim()) {
      metaEl.textContent = "与原译相同，无需保存。请先改正汉字。";
      return;
    }
    if (btnSaveCorrect) btnSaveCorrect.disabled = true;
    try {
      const payload = {
        braille: br,
        zh: zh,
        pred: pred || null,
        context: ((contextEl && contextEl.value) || "").trim() || null,
        row: selR,
        col: selC,
        table_id: "web",
        kind: "cell",
        meta: {
          backend: (backendEl && backendEl.value) || null,
        },
      };
      const res = await fetch("/v1/corrections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail || res.statusText || "保存失败";
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      // Update visible cell to corrected text
      if (tableCells[selR]) {
        tableCells[selR][selC] = zh;
        ensureCellAttrsFromCells();
        bindTableEvents();
        selectCell(selR, selC, { focus: false });
        mdOut.value = cellsToMarkdown(tableCells);
        csvOut.value = cellsToCsvClient(tableCells);
        if (resultEl) resultEl.value = cellsToFlat(tableCells);
      }
      metaEl.textContent = data.message || ("已保存纠错（共 " + (data.count || "?") + " 条）");
      await refreshCorrectStats();
    } catch (err) {
      metaEl.textContent = "纠错保存失败: " + err.message;
      setStatus("纠错保存失败: " + err.message, "err");
    } finally {
      if (btnSaveCorrect) btnSaveCorrect.disabled = false;
    }
  }

  async function doPrepareRetrain() {
    if (btnPrepareRetrain) btnPrepareRetrain.disabled = true;
    showRetrainBox("正在合并纠错并生成再训说明…", "warn");
    try {
      const res = await fetch("/v1/retrain/prepare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ include_user: true, include_holdout_errors: true }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail || res.statusText || "准备失败";
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      const n = (data.merge && data.merge.merged) || "?";
      const userN = (data.merge && data.merge.user_corrections) || 0;
      const cmd =
        (data.commands && data.commands.powershell_one_liner) ||
        "powershell -ExecutionPolicy Bypass -File scripts\\windows\\retrain_from_corrections.ps1";
      const after =
        (data.commands && data.commands.after_train_copy) || "";
      const msg =
        "已合并 " +
        n +
        " 条训练样本（含用户纠错 " +
        userN +
        " 条）。\n请在本机 Windows CUDA 环境运行：";
      if (retrainBox) {
        retrainBox.classList.remove("hidden", "ok", "warn", "err");
        retrainBox.classList.add("ok");
        retrainBox.innerHTML =
          escapeHtml(msg).replace(/\n/g, "<br/>") +
          '<code class="retrain-cmd">' +
          escapeHtml(cmd) +
          "</code>" +
          (after
            ? "<p style=\"margin:8px 0 0\">" + escapeHtml(after) + "</p>"
            : "");
      }
      metaEl.textContent =
        "再训已准备：合并 " + n + " 条。详见下方命令。";
      await refreshCorrectStats();
    } catch (err) {
      showRetrainBox("准备再训失败: " + err.message, "err");
      metaEl.textContent = "准备再训失败: " + err.message;
    } finally {
      if (btnPrepareRetrain) btnPrepareRetrain.disabled = false;
    }
  }

  async function refreshHealth() {
    try {
      const res = await fetch("/health", { cache: "no-store" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const h = await res.json();
      const lines = [
        "服务: 正常",
        "CUDA: " + (h.cuda ? "可用" + (h.gpu_name ? " — " + h.gpu_name : "") : "不可用"),
        "OCR: " + (h.ocr_ready ? "就绪 (OpenCV)" : "未安装 (pip install opencv-python-headless numpy Pillow)"),
        "适配器就绪: " + (h.adapter_ready ? "是" : "否") +
          (h.adapter_path ? " (" + h.adapter_path + ")" : ""),
        "已加载到显存: " + (h.adapter_loaded ? "是" : "否（首次翻译时加载）"),
      ];
      if (h.stub) lines.push("模式: CBT_QWEN_STUB=1（脚手架，不加载真模型）");
      setStatus(lines.join("\n"), h.cuda || h.stub ? "ok" : "warn");
    } catch (err) {
      setStatus("无法连接 /health：" + err.message, "err");
    }
  }

  function shouldUseTable(braille) {
    if (isFlatTable(braille)) return true;
    return !!(asTableEl && asTableEl.checked);
  }

  async function doTranslate() {
    const braille = (brailleEl.value || "").trim();
    if (!braille) {
      metaEl.textContent = "请先输入盲文。";
      brailleEl.focus();
      return;
    }
    btn.disabled = true;
    resultEl.value = "";
    clearTable();
    let progressTimer = null;
    const t0 = performance.now();
    try {
      const tabular = isFlatTable(braille);
      if (tabular && asTableEl) asTableEl.checked = true;
      const asTable = shouldUseTable(braille);
      let cellCount = 0;
      const gridForCount =
        asTable && inputCells.length
          ? inputCells
          : null;
      if (gridForCount) {
        for (const row of gridForCount) {
          for (const c of row || []) {
            if (String(c || "").trim()) cellCount++;
          }
        }
      }
      const payload = {
        braille,
        backend: backendEl.value || "qwen8b",
        as_table: asTable,
        max_new_tokens: asTable ? 32 : 128,
      };
      const ctx = (contextEl.value || "").trim();
      if (ctx) payload.context = ctx;
      // Prefer the editable input-grid shape so output rows/cols match.
      if (
        asTable &&
        inputCells.length &&
        inputCells.some((row) => (row || []).some((c) => String(c || "").trim()))
      ) {
        payload.cells = inputCells.map((row) =>
          (row || []).map((c) => String(c ?? ""))
        );
      }

      const tick = () => {
        const sec = ((performance.now() - t0) / 1000).toFixed(1);
        if (asTable && cellCount > 0) {
          metaEl.textContent =
            "翻译中… 已等待 " + sec + " 秒 · 约 " + cellCount +
            " 格（批量推理；首次冷启动可能数十秒）";
        } else {
          metaEl.textContent =
            "翻译中… 已等待 " + sec + " 秒（首次加载模型可能需要数十秒）";
        }
      };
      tick();
      progressTimer = setInterval(tick, 250);

      const res = await fetch("/v1/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail || res.statusText || "请求失败";
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      resultEl.value = data.text || "";
      showTable(data.table, data.text || "");
      metaEl.textContent =
        "后端: " + (data.backend || "?") + " · 耗时 " + (data.elapsed_s ?? "?") + " 秒" +
        (data.table ? " · 已按表格对应输出" : asTable ? " · 未返回表格" : "");
      refreshHealth();
    } catch (err) {
      resultEl.value = "";
      metaEl.textContent = "错误: " + err.message;
      setStatus("翻译失败: " + err.message, "err");
    } finally {
      if (progressTimer) clearInterval(progressTimer);
      btn.disabled = false;
    }
  }

  async function doPipeline() {
    const file = imageFile.files && imageFile.files[0];
    if (!file) {
      metaEl.textContent = "请先选择图片文件。";
      imageFile.focus();
      return;
    }
    btnPipeline.disabled = true;
    resultEl.value = "";
    clearTable();
    let progressTimer = null;
    const t0 = performance.now();
    progressTimer = setInterval(() => {
      const sec = ((performance.now() - t0) / 1000).toFixed(1);
      metaEl.textContent =
        "识别并翻译中… 已等待 " + sec + " 秒（OCR + 模型；冷启动可能较慢）";
    }, 250);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("backend", backendEl.value || "qwen8b");
      // Prefer table mode for pipeline (OCR tables)
      const asTable = asTableEl.checked || true;
      if (asTableEl) asTableEl.checked = true;
      fd.append("as_table", asTable ? "true" : "false");
      const ctx = (contextEl.value || "").trim();
      if (ctx) fd.append("context", ctx);

      const res = await fetch("/v1/pipeline", { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail || res.statusText || "请求失败";
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      if (data.braille) {
        brailleEl.value = data.braille;
        refreshInputTableFromTextarea();
      } else {
        metaEl.textContent =
          "OCR 未识别到盲文。若是网页 Unicode 表格截图请刷新后再试；" +
          "凸起点阵请用清晰实心圆点图。也可直接粘贴盲文到上方输入框。";
        setStatus("OCR 结果为空", "err");
      }
      resultEl.value = data.text || "";
      showTable(data.table, data.text || "");
      if (data.braille) {
        metaEl.textContent =
          "OCR: " + (data.ocr_method || "?") +
          " · 置信 " + (data.confidence ?? "?") +
          " · 后端: " + (data.backend || "?") +
          " · 耗时 " + (data.elapsed_s ?? "?") + " 秒";
      }
      refreshHealth();
    } catch (err) {
      resultEl.value = "";
      metaEl.textContent = "错误: " + err.message;
      setStatus("识别失败: " + err.message, "err");
    } finally {
      if (progressTimer) clearInterval(progressTimer);
      btnPipeline.disabled = false;
    }
  }

  document.querySelectorAll(".chip").forEach((el) => {
    el.addEventListener("click", () => {
      contextEl.value = el.getAttribute("data-ctx") || "";
      resultEl.value = "";
      const sampleId = el.getAttribute("data-sample");
      if (sampleId && SAMPLE_TABLES[sampleId]) {
        loadSampleGrid(SAMPLE_TABLES[sampleId], el.textContent.trim());
        return;
      }
      // Fallback: data-cells JSON (exact 2-D) — still never parseFlat for tables.
      const cellsRaw = el.getAttribute("data-cells");
      if (cellsRaw) {
        try {
          const grid = JSON.parse(cellsRaw);
          if (Array.isArray(grid) && grid.length && Array.isArray(grid[0])) {
            loadSampleGrid(grid, el.textContent.trim());
            return;
          }
        } catch (err) {
          console.warn("data-cells JSON parse failed", err);
        }
      }
      // Single-cell / non-table chips only.
      clearTable();
      clearInputTable();
      inputTableCollapsed = false;
      brailleEl.value = el.getAttribute("data-br") || "";
      if (el.getAttribute("data-table") === "1" || isFlatTable(brailleEl.value)) {
        if (asTableEl) asTableEl.checked = true;
        refreshInputTableFromTextarea();
      }
      metaEl.textContent = "已填入样例「" + el.textContent + "」，可点翻译。";
    });
  });

  btn.addEventListener("click", doTranslate);
  btnPipeline.addEventListener("click", doPipeline);
  btnClear.addEventListener("click", () => {
    brailleEl.value = "";
    contextEl.value = "";
    resultEl.value = "";
    metaEl.textContent = "";
    imageFile.value = "";
    clearTable();
    clearInputTable();
    inputTableCollapsed = false;
    brailleEl.focus();
  });

  if (btnHideInputTable) {
    btnHideInputTable.addEventListener("click", () => {
      inputTableCollapsed = true;
      if (inputTableWrap) inputTableWrap.classList.add("hidden");
    });
  }

  brailleEl.addEventListener("input", () => {
    refreshInputTableFromTextarea();
  });
  brailleEl.addEventListener("paste", () => {
    // After paste content lands in textarea
    setTimeout(refreshInputTableFromTextarea, 0);
  });

  if (btnJump) btnJump.addEventListener("click", doJump);
  if (btnSpeakCell) btnSpeakCell.addEventListener("click", speakCell);
  if (btnSpeakRow) btnSpeakRow.addEventListener("click", speakRow);
  if (btnSpeakTable) btnSpeakTable.addEventListener("click", speakTable);
  if (btnSpeakStop) btnSpeakStop.addEventListener("click", stopSpeak);

  brailleEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      doTranslate();
    }
  });

  if (btnSaveCorrect) btnSaveCorrect.addEventListener("click", doSaveCorrect);
  if (btnPrepareRetrain) btnPrepareRetrain.addEventListener("click", doPrepareRetrain);
  if (btnRefreshCorrectStats) {
    btnRefreshCorrectStats.addEventListener("click", () => refreshCorrectStats());
  }
  if (correctZhEl) {
    correctZhEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        doSaveCorrect();
      }
    });
  }

  refreshHealth();
  refreshCorrectStats();
  refreshInputTableFromTextarea();
})();
