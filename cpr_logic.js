function getZoneLabel(c, pivot, tc, bc, r1, r2, s1, s2) {
    const upper = Math.max(tc, bc);
    const lower = Math.min(tc, bc);
    const r3 = r1 + (r1 - s1);
    const r4 = r3 + (r1 - s1);
    const s3 = s1 - (r1 - s1);
    const s4 = s3 - (r1 - s1);
    if (c >= r4) return "▲R4";
    if (c >= r3) return "▲R3";
    if (c >= r2) return "▲R2";
    if (c >= r1) return "▲R1";
    if (c >= upper) return "▲Pvt";
    if (c >= lower) return "InCPR";
    if (c >= pivot) return "▼TC";
    if (c >= s1) return "▼Pvt";
    if (c >= s2) return "▼S1";
    if (c >= s3) return "▼S2";
    if (c >= s4) return "▼S3";
    return "▼S4";
}

function getDailyCode(c, tc, bc, r1, s1, pdh, pdl) {
    const upper = Math.max(tc, bc);
    const lower = Math.min(tc, bc);
    const abv = c > upper;
    const blw = c < lower;
    if (abv && (c > r1 || c > pdh)) return "VBull";
    if (blw && (c < s1 || c < pdl)) return "VBear";
    if (abv) return "WBull";
    if (blw) return "WBear";
    return "Neutral";
}

function getWeeklyCode(c, wpiv) {
    return c >= wpiv ? "WBull" : "WBear";
}

function getBias(dCode, wCode) {
    const bullCodes = ["WBull", "VBull", "Neutral"];
    const bearCodes = ["WBear", "VBear", "Neutral"];
    if (wCode === "WBull" && bullCodes.includes(dCode)) return "BULL";
    if (wCode === "WBear" && bearCodes.includes(dCode)) return "BEAR";
    return "NONE";
}

function nearLevel(val, lvl, thresh) {
    if (!lvl || lvl <= 0) return false;
    return Math.abs(val - lvl) / lvl <= thresh;
}

function checkOne(lc, lvl, name, thresh) {
    if (!lvl || lvl <= 0.0) return ["", 999.0];
    const d = Math.abs(lc - lvl) / lvl;
    if (d <= thresh) {
        let ok = true;
        if (name === "R1" || name === "PDH") ok = lc < lvl;
        else if (name === "S1" || name === "PDL") ok = lc > lvl;
        if (ok) return [name, d];
    }
    return ["", 999.0];
}

function lvlEval(lc, pdh, pdl, r1, s1, thresh) {
    const [n1, d1] = checkOne(lc, pdh, "PDH", thresh);
    const [n2, d2] = checkOne(lc, pdl, "PDL", thresh);
    const [n3, d3] = checkOne(lc, r1, "R1", thresh);
    const [n4, d4] = checkOne(lc, s1, "S1", thresh);
    if (d1 <= d2 && d1 <= d3 && d1 <= d4) return n1;
    if (d2 <= d3 && d2 <= d4) return n2;
    if (d3 <= d4) return n3;
    return n4;
}

function getNextLevelDist(z, dt, db, dp, dr1, dr2, dr3, dr4, ds1, ds2, ds3, ds4) {
    const rg = dr1 - ds1;
    let lvlFrom = null;
    let lvlTo = null;
    
    if (z === "▲R1") { lvlFrom = dr1; lvlTo = dr2; }
    else if (z === "▲R2") { lvlFrom = dr2; lvlTo = dr3; }
    else if (z === "▲R3") { lvlFrom = dr3; lvlTo = dr4; }
    else if (z === "▲R4") { lvlFrom = dr4; lvlTo = dr4 + rg; }
    else if (z === "▲Pvt") { lvlFrom = Math.max(dt, db); lvlTo = dr1; }
    else if (z === "InCPR") { lvlFrom = Math.min(dt, db); lvlTo = Math.max(dt, db); }
    else if (z === "▼TC") { lvlFrom = dp; lvlTo = Math.max(dt, db); }
    else if (z === "▼Pvt") { lvlFrom = ds1; lvlTo = dp; }
    else if (z === "▼S1") { lvlFrom = ds2; lvlTo = ds1; }
    else if (z === "▼S2") { lvlFrom = ds3; lvlTo = ds2; }
    else if (z === "▼S3") { lvlFrom = ds4; lvlTo = ds3; }
    else if (z === "▼S4") { lvlFrom = ds4 - rg; lvlTo = ds4; }
    
    if (lvlFrom && lvlFrom > 0) {
        return (Math.abs(lvlTo - lvlFrom) / lvlFrom) * 100.0;
    }
    return null;
}

// Function to update the symbol's computed values based on new live price/volume
function updateSymbolLogic(row, ltp, highPrice, lowPrice, openPrice, volume, pdvol, pctElapsed) {
    // Basic setup from the row
    row.live_price = ltp;
    row.close = ltp;
    const _lc = ltp;
    const _currH = highPrice;
    const _currL = lowPrice;
    const _dopen = openPrice;
    const _dvol = volume;
    
    const _dtc = row.tc;
    const _dbc = row.bc;
    const _dpiv = row.pivot;
    const _dr1 = row.r1;
    const _dr2 = row.r2;
    const _ds1 = row.s1;
    const _ds2 = row.s2;
    const _dr3 = row.dr3;
    const _dr4 = row.dr4;
    const _ds3 = row.ds3;
    const _ds4 = row.ds4;
    const _pdh = row.pdh;
    const _pdl = row.pdl;
    
    const _wpiv = row.weekly_pivot;
    const _wtc = row.weekly_tc;
    const _wbc = row.weekly_bc;
    const _wr1 = row.weekly_r1;
    const _ws1 = row.weekly_s1;
    const _wh2 = row.wh2;
    const _wl2 = row.wl2;
    
    // We only recalculate wZone, but wait: Python calculates _wr2, _ws2 which we didn't export!
    // We need _wr2 and _ws2. _wr2 = _wpiv + (_wh2 - _wl2). _ws2 = _wpiv - (_wh2 - _wl2).
    const _wr2 = _wpiv + (_wh2 - _wl2);
    const _ws2 = _wpiv - (_wh2 - _wl2);

    const dCode = getDailyCode(_lc, _dtc, _dbc, _dr1, _ds1, _pdh, _pdl);
    const wCode = getWeeklyCode(_lc, _wpiv);
    row.dZone = getZoneLabel(_lc, _dpiv, _dtc, _dbc, _dr1, _dr2, _ds1, _ds2);
    row.wZone = getZoneLabel(_lc, _wpiv, _wtc, _wbc, _wr1, _wr2, _ws1, _ws2);
    row.bias = getBias(dCode, wCode);
    
    if (pdvol && pdvol > 0 && pctElapsed > 0) {
        row.vRatio = Number((_dvol / (pdvol * pctElapsed)).toFixed(2));
    } else {
        row.vRatio = 0.0;
    }
    
    // Reversal Logic
    const _tol = 0.001;
    const _reachedTop = _currH >= Math.min(_dr1, _pdh) * (1 - _tol);
    const _reachedBot = _currL <= Math.max(_ds1, _pdl) * (1 + _tol);
    const _bearRev = _reachedTop && _currH < _dr2 && _lc < _dbc;
    const _bullRev = _reachedBot && _currL > _ds2 && _lc > _dtc;
    
    row.revStr = "";
    if (_bearRev && _bullRev) row.revStr = _lc < _dpiv ? "BearRev" : "BullRev";
    else if (_bearRev) row.revStr = "BearRev";
    else if (_bullRev) row.revStr = "BullRev";
    
    // Near Level
    const _nl = lvlEval(_lc, _pdh, _pdl, _dr1, _ds1, 0.003);
    row.apB = (_nl === "R1" || _nl === "PDH") && ["Neutral", "WBull", "VBull"].includes(dCode) && ["Neutral", "WBull", "VBull"].includes(wCode);
    row.apBr = (_nl === "S1" || _nl === "PDL") && ["Neutral", "WBear", "VBear"].includes(dCode) && ["Neutral", "WBear", "VBear"].includes(wCode);
    
    // Setup Signal
    function openedNear(op, tc, bc, piv, klvl, phl, t) {
        return nearLevel(op, tc, t) || nearLevel(op, bc, t) || nearLevel(op, piv, t) || nearLevel(op, klvl, t) || nearLevel(op, phl, t);
    }
    const nearDBear = openedNear(_dopen, _dtc, _dbc, _dpiv, _ds1, _wl2, 0.006);
    const nearWBear = openedNear(_dopen, _wtc, _wbc, _wpiv, _ws1, _wl2, 0.003);
    const nearDBull = openedNear(_dopen, _dtc, _dbc, _dpiv, _dr1, _pdh, 0.006);
    const nearWBull = openedNear(_dopen, _wtc, _wbc, _wpiv, _wr1, _wh2, 0.003);
    
    const isBear = row.bias === "BEAR" || row.bias === "Both";
    const isBull = row.bias === "BULL" || row.bias === "Both";
    const bearSetup = isBear && nearDBear && nearWBear;
    const bullSetup = isBull && nearDBull && nearWBull;
    
    const sig = (bearSetup && bullSetup) ? 1 : bearSetup ? -1 : bullSetup ? 1 : 0;
    let wDist = 999.0;
    if (sig !== 0) {
        const l4 = sig === -1 ? _ws1 : _wr1;
        const l5 = sig === -1 ? _wl2 : _wh2;
        const levels = [_wtc, _wbc, _wpiv, l4, l5].filter(l => l > 0);
        if (levels.length > 0) {
            wDist = Math.min(...levels.map(l => Math.abs(_dopen - l) / l));
        }
    }
    row.setup = `${sig}|${wDist}`;
    
    const nlPct = getNextLevelDist(row.dZone, _dtc, _dbc, _dpiv, _dr1, _dr2, _dr3, _dr4, _ds1, _ds2, _ds3, _ds4);
    row.nl_pct = nlPct ? Number(nlPct.toFixed(2)) : null;
    
    // Score Calculation
    let score = -1.0;
    if (sig !== 0 && row.nl_pct !== null && row.nl_pct > 0) {
        let volMult = row.vRatio > 0 ? row.vRatio : 1.0;
        score = row.nl_pct * volMult;
    }
    row.score = score;
    row.rank = 0; // Will be assigned globally
}

function assignRanks(allData) {
    // Sort descending by score
    allData.sort((a, b) => (b.score || -1) - (a.score || -1));
    let currentRank = 1;
    for (let i = 0; i < allData.length; i++) {
        if (allData[i].score !== undefined && allData[i].score > 0) {
            allData[i].rank = currentRank++;
        } else {
            allData[i].rank = 0;
        }
    }
}
