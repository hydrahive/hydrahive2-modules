package io.hydrahive.app;

import android.content.Context;
import android.content.SharedPreferences;

/** Gemerkte Kopplung: Server, Schlüssel-Pin (oder leer bei öffentlicher Adresse), Geräte-Schlüssel, Name. */
final class Store {
    private final SharedPreferences p;

    Store(Context ctx) { p = ctx.getSharedPreferences("hydra", Context.MODE_PRIVATE); }

    String server() { return p.getString("server", ""); }
    String pin() { return p.getString("pin", ""); }
    String token() { return p.getString("token", ""); }
    String name() { return p.getString("name", ""); }
    boolean paired() { return !server().isEmpty() && !token().isEmpty(); }

    void save(String server, String pin, String token, String name) {
        p.edit().putString("server", server).putString("pin", pin == null ? "" : pin)
                .putString("token", token).putString("name", name).apply();
    }

    void clear() { p.edit().clear().apply(); }
}
