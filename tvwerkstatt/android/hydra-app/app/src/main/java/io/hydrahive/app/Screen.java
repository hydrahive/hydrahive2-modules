package io.hydrahive.app;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.StateListDrawable;
import android.text.InputType;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** Ansicht ohne Layout-Dateien: Einrichten, Fingerabdruck bestätigen, gekoppelt. Bedienbar mit Fernbedienung und Touch. */
final class Screen {
    private static final int BG = Color.rgb(11, 18, 32), TEXT = Color.rgb(232, 238, 248), MUTED = Color.rgb(154, 167, 188);
    private static final int ACCENT = Color.rgb(105, 215, 255), FIELD = Color.rgb(22, 32, 52), OK = Color.rgb(110, 231, 183);
    final ScrollView root;
    private final Activity a;
    private final boolean tv;
    private final LinearLayout box;
    private EditText server, code;
    private TextView msg, state;

    Screen(Activity a, boolean tv) {
        this.a = a;
        this.tv = tv;
        root = new ScrollView(a);
        root.setBackgroundColor(BG);
        root.setFillViewport(true);
        box = new LinearLayout(a);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setGravity(Gravity.CENTER_HORIZONTAL);
        int pad = dp(tv ? 48 : 24);
        box.setPadding(pad, pad, pad, pad);
        root.addView(box, new ScrollView.LayoutParams(-1, -2));
    }

    String server() { return server == null ? "" : server.getText().toString(); }
    String code() { return code == null ? "" : code.getText().toString(); }

    void setup(View.OnClickListener onGo) {
        String s = server(), c = code();
        start("HydraHive verbinden");
        text("In der TV-Werkstatt im Reiter Geräte einen Code erzeugen und hier mit der Adresse eintippen.", MUTED, 16);
        server = field("Adresse, z. B. https://192.168.178.2", s.isEmpty() ? "https://" : s,
                InputType.TYPE_TEXT_VARIATION_URI);
        code = field("Code, z. B. K7QM-2XPA-B3CD", c, InputType.TYPE_TEXT_FLAG_CAP_CHARACTERS);
        Button go = button("Weiter", onGo);
        msg = text("", ACCENT, 16);
        (s.isEmpty() || s.equals("https://") ? server : go).requestFocus();
    }

    void confirm(String shortPin, View.OnClickListener yes, View.OnClickListener no) {
        start("Fingerabdruck vergleichen");
        text("Steht in der Werkstatt neben dem Code derselbe Fingerabdruck?", MUTED, 16);
        TextView p = text(shortPin, ACCENT, 34);
        p.setTypeface(Typeface.MONOSPACE, Typeface.BOLD);
        Button ok = button("Stimmt, koppeln", yes);
        button("Stimmt nicht", no);
        msg = text("", ACCENT, 16);
        ok.requestFocus();
    }

    void paired(String name, String server, String shortPin, View.OnClickListener onUnpair) {
        start("HydraHive");
        text("Verbunden als „" + name + "“", TEXT, 22);
        state = text("Verbinde …", MUTED, 18);
        text(server + (shortPin.isEmpty() ? "" : "  ·  " + shortPin), MUTED, 14);
        text("Einblendungen von Hydra kommen in einer der nächsten Versionen.", MUTED, 14);
        button("Kopplung löschen", onUnpair);
        msg = text("", ACCENT, 16);
    }

    void online(boolean on) {
        if (state == null) return;
        state.setText(on ? "● verbunden" : "○ nicht verbunden – versuche es weiter");
        state.setTextColor(on ? OK : MUTED);
    }

    void message(String m) { if (msg != null) msg.setText(m); }

    private void start(String title) {
        box.removeAllViews();
        server = code = null;
        msg = state = null;
        TextView t = text(title, TEXT, 28);
        t.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
    }

    private TextView text(String s, int color, int sp) {
        TextView t = new TextView(a);
        t.setText(s);
        t.setTextColor(color);
        t.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp);
        t.setGravity(Gravity.CENTER_HORIZONTAL);
        add(t, dp(8));
        return t;
    }

    private EditText field(String hint, String value, int variation) {
        EditText e = new EditText(a);
        e.setHint(hint);
        e.setText(value);
        e.setSingleLine(true);
        e.setInputType(InputType.TYPE_CLASS_TEXT | variation);
        e.setTextColor(TEXT);
        e.setHintTextColor(MUTED);
        e.setTextSize(TypedValue.COMPLEX_UNIT_SP, 20);
        e.setBackground(frame(FIELD));
        e.setPadding(dp(14), dp(10), dp(14), dp(10));
        add(e, dp(10));
        return e;
    }

    private Button button(String label, View.OnClickListener l) {
        Button b = new Button(a);
        b.setText(label);
        b.setAllCaps(false);
        b.setTextColor(TEXT);
        b.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18);
        b.setBackground(frame(FIELD));
        b.setOnClickListener(l);
        add(b, dp(10));
        return b;
    }

    /** Rahmen, der beim Fokus (Fernbedienung) in Akzentfarbe leuchtet. */
    private StateListDrawable frame(int fill) {
        StateListDrawable s = new StateListDrawable();
        s.addState(new int[]{android.R.attr.state_focused}, rect(fill, ACCENT, 3));
        s.addState(new int[]{android.R.attr.state_pressed}, rect(fill, ACCENT, 3));
        s.addState(new int[]{}, rect(fill, MUTED, 1));
        return s;
    }

    private GradientDrawable rect(int fill, int line, int width) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(fill);
        g.setCornerRadius(dp(10));
        g.setStroke(dp(width), line);
        return g;
    }

    private void add(View v, int top) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(Math.min(dp(tv ? 640 : 520),
                a.getResources().getDisplayMetrics().widthPixels - dp(48)), -2);
        lp.topMargin = top;
        box.addView(v, lp);
    }

    private int dp(int v) { return Math.round(v * a.getResources().getDisplayMetrics().density); }
}
