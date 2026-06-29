// control.scd — Signal Lab's hands-on control panel.
// 1) Evaluate engine.scd first (boots scsynth + the SynthDefs).
// 2) Then evaluate this whole block (Cmd+Enter inside the parens).
// A window opens with a column of knobs per instrument, a play button, and live
// scope + spectrum. Turn the knobs, hit play, watch the sound — sculpt by hand.
(
var win, col, dur;
dur = 2.5;
win = Window("Signal Lab — Control", Rect(60, 80, 1000, 560)).front;
win.layout = HLayout();

col = { |name, defname, specs, freqDefault = 220, useFreq = true|
    var v = View().layout_(VLayout()), ezs = [], freqSl, play;
    v.layout.add(StaticText().string_(name).font_(Font("Monaco", 15, true)).align_(\center));
    if (useFreq) {
        freqSl = EZSlider(v, 210 @ 24, "freq", ControlSpec(40, 2000, \exp),
            initVal: freqDefault, labelWidth: 66, numberWidth: 56);
    };
    specs.do { |sp|
        var ez = EZSlider(v, 210 @ 24, sp[0].asString,
            ControlSpec(sp[1], sp[2], sp[3] ? \lin), initVal: sp[4],
            labelWidth: 66, numberWidth: 56);
        ezs = ezs.add([sp[0], ez]);
    };
    play = Button(v, 210 @ 34).states_([["▶  play " ++ name]])
        .action_({
            var args = [\dur, dur];
            if (useFreq) { args = args ++ [\freq, freqSl.value] };
            ezs.do { |p| args = args ++ [p[0], p[1].value] };
            Synth(defname, args);
        });
    win.layout.add(v);
};

col.("Subtractive", \labvoice, [
    [\wave, 0, 3, \lin, 0], [\cutoff, 60, 12000, \exp, 1500], [\rq, 0.05, 1, \lin, 0.4],
    [\atk, 0, 3, \lin, 0.05], [\rel, 0, 4, \lin, 0.4], [\revmix, 0, 0.9, \lin, 0.3],
    [\detune, 0, 30, \lin, 8], [\voices, 1, 3, \lin, 1], [\pan, -1, 1, \lin, 0]], 220);

col.("FM", \labfm, [
    [\ratio, 0.5, 8, \lin, 2], [\index, 0, 12, \lin, 3], [\cutoff, 60, 12000, \exp, 4000],
    [\atk, 0, 2, \lin, 0.01], [\rel, 0, 4, \lin, 1], [\revmix, 0, 0.9, \lin, 0.4]], 220);

col.("Stardust", \stardust, [
    [\density, 1, 30, \lin, 7], [\lo, 400, 8000, \exp, 1500], [\hi, 800, 12000, \exp, 4500],
    [\amp, 0, 0.3, \lin, 0.12], [\revmix, 0, 0.9, \lin, 0.6], [\dur, 1, 14, \lin, 6]], 0, false);

// live visualization
FreqScope.new(440, 220, 0, server: s);
s.scope(2);

"Signal Lab control panel open — turn knobs, hit play, watch the scopes.".postln;
)
