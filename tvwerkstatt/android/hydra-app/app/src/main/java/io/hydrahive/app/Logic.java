package io.hydrahive.app;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Reine Logik ohne Android – einzeln getestet (LogicTest). Gegenstück im Server: backend/app_tls.py, app_pairing.py. */
final class Logic {
    static final String ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
    static final int CODE_LEN = 12;
    private static final Pattern SERVER = Pattern.compile(
            "^https://(\\[[0-9a-f:.]+\\]|[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?)(:([0-9]{1,5}))?$");
    private static final String[] LOCAL_SUFFIXES = {".local", ".lan", ".home", ".internal", ".localdomain",
            ".home.arpa", ".fritz.box"};

    private Logic() {}

    /** Eingabe → „https://host[:port]“ oder null. Ohne Schema wird https ergänzt; „http://…“ fällt durch das Muster. */
    static String normalizeServer(String raw) {
        if (raw == null) return null;
        String s = raw.trim().toLowerCase(Locale.ROOT);
        while (s.endsWith("/")) s = s.substring(0, s.length() - 1);
        if (!s.startsWith("https://")) s = "https://" + s;
        Matcher m = SERVER.matcher(s);
        if (!m.matches()) return null;
        if (m.group(4) != null) {
            int port = Integer.parseInt(m.group(4));
            if (port < 1 || port > 65535) return null;
        }
        return s;
    }

    /** Host aus einer normalisierten Adresse (IPv6 ohne Klammern). */
    static String hostOf(String server) {
        Matcher m = SERVER.matcher(server == null ? "" : server);
        if (!m.matches()) return "";
        String h = m.group(1);
        return h.startsWith("[") ? h.substring(1, h.length() - 1) : h;
    }

    /** Wie app_tls.is_local: private Adressen und Namen im Heimnetz. Nur dort prüft die App den Fingerabdruck. */
    static boolean isLocal(String host) {
        String h = host == null ? "" : host.toLowerCase(Locale.ROOT);
        if (h.isEmpty()) return false;
        if (h.contains(":")) return h.equals("::1") || h.startsWith("fc") || h.startsWith("fd") || h.startsWith("fe80");
        int[] ip = ipv4(h);
        if (ip != null) {
            return ip[0] == 10 || ip[0] == 127 || (ip[0] == 172 && ip[1] >= 16 && ip[1] <= 31)
                    || (ip[0] == 192 && ip[1] == 168) || (ip[0] == 169 && ip[1] == 254);
        }
        if (!h.contains(".")) return true;
        for (String suf : LOCAL_SUFFIXES) if (h.endsWith(suf)) return true;
        return false;
    }

    private static int[] ipv4(String h) {
        String[] p = h.split("\\.", -1);
        if (p.length != 4) return null;
        int[] out = new int[4];
        for (int i = 0; i < 4; i++) {
            if (p[i].isEmpty() || p[i].length() > 3 || !p[i].matches("[0-9]+")) return null;
            out[i] = Integer.parseInt(p[i]);
            if (out[i] > 255) return null;
        }
        return out;
    }

    /** Code säubern (Leerzeichen, Bindestriche weg, groß) → 12 Zeichen aus dem Alphabet, sonst null. */
    static String cleanCode(String raw) {
        if (raw == null) return null;
        String c = raw.replaceAll("[\\s-]", "").toUpperCase(Locale.ROOT);
        if (c.length() != CODE_LEN) return null;
        for (int i = 0; i < c.length(); i++) if (ALPHABET.indexOf(c.charAt(i)) < 0) return null;
        return c;
    }

    /** SHA-256 des öffentlichen Schlüssels (SPKI, DER) als Kleinbuchstaben-Hex. */
    static String spkiHex(byte[] spkiDer) {
        try {
            byte[] d = MessageDigest.getInstance("SHA-256").digest(spkiDer);
            StringBuilder sb = new StringBuilder(64);
            for (byte b : d) sb.append(String.format(Locale.ROOT, "%02x", b & 0xff));
            return sb.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    /** Kurzer Fingerabdruck zum Vergleichen mit der Werkstatt: die ersten 12 Hex-Zeichen, groß, in Vierergruppen. */
    static String shortPin(String hex) {
        if (hex == null || !hex.matches("[0-9a-f]{64}")) return "";
        String s = hex.substring(0, 12).toUpperCase(Locale.ROOT);
        return s.substring(0, 4) + " " + s.substring(4, 8) + " " + s.substring(8, 12);
    }
}
