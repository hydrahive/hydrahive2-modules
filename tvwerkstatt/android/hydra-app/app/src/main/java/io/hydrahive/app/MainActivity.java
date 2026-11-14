package io.hydrahive.app;

import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import java.io.IOException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONException;
import org.json.JSONObject;

/** Eine Seite: einrichten (Server + Code), Fingerabdruck vergleichen, gekoppelt mit Lebenszeichen alle 25 s. */
public class MainActivity extends Activity {
    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final Runnable tick = this::hello;
    private Store store;
    private Screen screen;
    private int pollSeconds = 25;
    private boolean resumed;

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        store = new Store(this);
        screen = new Screen(this, tv());
        setContentView(screen.root);
        show();
    }

    @Override protected void onResume() { super.onResume(); resumed = true; if (store.paired()) hello(); }

    @Override protected void onPause() { super.onPause(); resumed = false; ui.removeCallbacks(tick); }

    @Override protected void onDestroy() { io.shutdownNow(); super.onDestroy(); }

    private boolean tv() {
        PackageManager pm = getPackageManager();
        return pm.hasSystemFeature(PackageManager.FEATURE_LEANBACK);
    }

    private void show() {
        if (store.paired()) {
            screen.paired(store.name(), store.server(), Logic.shortPin(store.pin()), v -> unpair());
        } else {
            screen.setup(v -> start());
        }
    }

    /** Schritt 1: Eingaben prüfen; lokal erst den Fingerabdruck lesen und zeigen, sonst gleich koppeln. */
    private void start() {
        String server = Logic.normalizeServer(screen.server());
        String code = Logic.cleanCode(screen.code());
        if (server == null) { screen.message("Adresse bitte als https://… eingeben."); return; }
        if (code == null) { screen.message("Der Code hat 12 Zeichen, z. B. K7QM-2XPA-B3CD."); return; }
        if (!Logic.isLocal(Logic.hostOf(server))) { enroll(server, null, code); return; }
        screen.message("Verbinde …");
        io.execute(() -> {
            try {
                String pin = Net.readPin(server);
                ui.post(() -> screen.confirm(Logic.shortPin(pin), v -> enroll(server, pin, code), v -> show()));
            } catch (IOException e) {
                ui.post(() -> screen.message("Server nicht erreichbar. Adresse prüfen."));
            }
        });
    }

    /** Schritt 2: Code gegen Schlüssel tauschen. */
    private void enroll(String server, String pin, String code) {
        screen.message("Kopple …");
        io.execute(() -> {
            String msg;
            try {
                JSONObject info = new JSONObject().put("kind", tv() ? "tv" : "tablet")
                        .put("model", (Build.MANUFACTURER + " " + Build.MODEL).trim())
                        .put("android", Build.VERSION.RELEASE).put("app_version", BuildConfig.VERSION_NAME);
                Net.Reply r = Net.call(server, pin, "POST", "enroll", new JSONObject().put("info", info).toString(),
                        null, code, 15000);
                if (Net.ok(r.status)) {
                    JSONObject o = new JSONObject(r.body);
                    store.save(server, pin, o.getString("token"), o.optString("name", ""));
                    ui.post(() -> { show(); hello(); });
                    return;
                }
                msg = r.status == 409 ? "Diesen Namen hat schon ein Gerät. In der Werkstatt einen anderen wählen."
                        : r.status == 429 ? "Zu viele Versuche. Bitte kurz warten."
                        : "Code falsch, abgelaufen oder schon benutzt.";
            } catch (IOException e) {
                msg = "Verbindung abgebrochen. Stimmt der Fingerabdruck noch?";
            } catch (JSONException e) {
                msg = "Unerwartete Antwort vom Server.";
            }
            String m = msg;
            ui.post(() -> { screen.setup(v -> start()); screen.message(m); });
        });
    }

    /** Lebenszeichen; 401 = gesperrt → zurück zum Einrichten. */
    private void hello() {
        ui.removeCallbacks(tick);
        if (!store.paired()) return;
        String server = store.server(), pin = store.pin().isEmpty() ? null : store.pin(), token = store.token();
        io.execute(() -> {
            int st;
            try {
                JSONObject state = new JSONObject().put("screen", "on").put("app", "open");
                Net.Reply r = Net.call(server, pin, "POST", "hello", new JSONObject().put("state", state).toString(),
                        token, null, 15000);
                st = r.status;
                if (Net.ok(st)) pollSeconds = Math.max(10, Math.min(300, new JSONObject(r.body).optInt("poll_seconds", 25)));
            } catch (IOException | JSONException e) {
                st = -1;
            }
            int status = st;
            ui.post(() -> {
                if (status == 401) {
                    store.clear();
                    show();
                    screen.message("Dieses Gerät wurde in der Werkstatt gesperrt. Bitte neu koppeln.");
                    return;
                }
                screen.online(Net.ok(status));
                if (resumed) ui.postDelayed(tick, pollSeconds * 1000L);
            });
        });
    }

    private void unpair() {
        store.clear();
        ui.removeCallbacks(tick);
        show();
        screen.message("Kopplung auf diesem Gerät gelöscht. In der Werkstatt das Gerät noch sperren.");
    }
}
