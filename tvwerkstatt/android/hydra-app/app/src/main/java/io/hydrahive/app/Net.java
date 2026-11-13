package io.hydrahive.app;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;

/** Verbindung zu Hydra. Lokal: nur der gemerkte Schlüssel (Pin) zählt, nicht der Name. Sonst: normale Prüfung. */
final class Net {
    static final String BASE = "/api/module-device/tvwerkstatt/app/";
    private static final int MAX_BODY = 64 * 1024;

    /** Antwort: Status und Text (höchstens 64 KB). */
    static final class Reply {
        final int status;
        final String body;
        Reply(int status, String body) { this.status = status; this.body = body; }
    }

    private Net() {}

    /** Prüft genau einen Schlüssel. Ohne Pin (null) wird nur gelesen, was der Server zeigt (seen) – und abgelehnt. */
    static final class PinTrust implements X509TrustManager {
        final String pin;
        String seen = "";
        PinTrust(String pin) { this.pin = pin; }

        @Override public void checkServerTrusted(X509Certificate[] chain, String authType) throws CertificateException {
            if (chain == null || chain.length == 0) throw new CertificateException("kein Zertifikat");
            seen = Logic.spkiHex(chain[0].getPublicKey().getEncoded());
            if (pin == null || !pin.equals(seen)) throw new CertificateException("Schlüssel passt nicht");
        }
        @Override public void checkClientTrusted(X509Certificate[] chain, String authType) throws CertificateException {
            throw new CertificateException("nicht vorgesehen");
        }
        @Override public X509Certificate[] getAcceptedIssuers() { return new X509Certificate[0]; }
    }

    private static SSLSocketFactory factory(PinTrust t) throws IOException {
        try {
            SSLContext ctx = SSLContext.getInstance("TLS");
            ctx.init(null, new TrustManager[]{t}, null);
            return ctx.getSocketFactory();
        } catch (java.security.GeneralSecurityException e) {
            throw new IOException(e);
        }
    }

    /** Liest den Fingerabdruck (SHA-256-Hex des Schlüssels) eines lokalen Servers, ohne etwas zu schicken. */
    static String readPin(String server) throws IOException {
        PinTrust t = new PinTrust(null);
        HttpsURLConnection c = (HttpsURLConnection) new URL(server + "/").openConnection();
        c.setSSLSocketFactory(factory(t));
        c.setHostnameVerifier((h, s) -> true);           // Name egal: verglichen wird nur der Schlüssel
        c.setConnectTimeout(8000);
        c.setReadTimeout(8000);
        try {
            c.connect();
        } catch (IOException expected) {
            // Gewollt: ohne Pin bricht der Handschlag ab, nachdem der Schlüssel gelesen ist.
        } finally {
            c.disconnect();
        }
        if (t.seen.isEmpty()) throw new IOException("Server nicht erreichbar");
        return t.seen;
    }

    /** Anfrage an eine Geräte-Route. pin != null → nur dieser Schlüssel; pin == null → normale Prüfung. */
    static Reply call(String server, String pin, String method, String path, String json,
                      String token, String pairingCode, int timeoutMs) throws IOException {
        HttpsURLConnection c = (HttpsURLConnection) new URL(server + BASE + path).openConnection();
        if (pin != null) {
            c.setSSLSocketFactory(factory(new PinTrust(pin)));
            c.setHostnameVerifier((h, s) -> true);       // Name egal, der Schlüssel ist festgenagelt
        }
        c.setConnectTimeout(8000);
        c.setReadTimeout(timeoutMs);
        c.setUseCaches(false);
        c.setRequestMethod(method);
        c.setRequestProperty("Accept", "application/json");
        if (token != null) c.setRequestProperty("Authorization", "Bearer " + token);
        if (pairingCode != null) c.setRequestProperty("X-Pairing-Code", pairingCode);
        try {
            if (json != null) {
                byte[] b = json.getBytes(StandardCharsets.UTF_8);
                c.setDoOutput(true);
                c.setRequestProperty("Content-Type", "application/json");
                c.setFixedLengthStreamingMode(b.length);
                try (OutputStream o = c.getOutputStream()) { o.write(b); }
            }
            int st = c.getResponseCode();
            InputStream in = st >= 400 ? c.getErrorStream() : c.getInputStream();
            return new Reply(st, in == null ? "" : read(in));
        } finally {
            c.disconnect();
        }
    }

    private static String read(InputStream in) throws IOException {
        try (InputStream i = in) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            int n;
            while ((n = i.read(buf)) > 0) {
                if (out.size() + n > MAX_BODY) throw new IOException("Antwort zu groß");
                out.write(buf, 0, n);
            }
            return out.toString("UTF-8");
        }
    }

    static boolean ok(int status) { return status >= 200 && status < 300; }
}
