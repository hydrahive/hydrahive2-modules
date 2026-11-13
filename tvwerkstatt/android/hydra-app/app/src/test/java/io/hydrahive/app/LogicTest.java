package io.hydrahive.app;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.nio.charset.StandardCharsets;
import org.junit.Test;

public class LogicTest {
    @Test public void serverWirdNormalisiert() {
        assertEquals("https://192.168.178.2", Logic.normalizeServer(" 192.168.178.2/ "));
        assertEquals("https://hydra.fritz.box:8443", Logic.normalizeServer("HTTPS://Hydra.Fritz.Box:8443/"));
        assertEquals("https://[fd00::2]", Logic.normalizeServer("https://[fd00::2]"));
    }

    @Test public void serverOhneVerschluesselungOderKaputtAbgelehnt() {
        assertNull(Logic.normalizeServer("http://192.168.178.2"));
        assertNull(Logic.normalizeServer("https://192.168.178.2/api"));
        assertNull(Logic.normalizeServer("https://host:70000"));
        assertNull(Logic.normalizeServer("https://host:0"));
        assertNull(Logic.normalizeServer("https://ho st"));
        assertNull(Logic.normalizeServer("https://user@host"));
        assertNull(Logic.normalizeServer(""));
        assertNull(Logic.normalizeServer(null));
    }

    @Test public void hostAusAdresse() {
        assertEquals("192.168.178.2", Logic.hostOf("https://192.168.178.2:8443"));
        assertEquals("fd00::2", Logic.hostOf("https://[fd00::2]"));
        assertEquals("", Logic.hostOf("kaputt"));
    }

    @Test public void lokalWieDerServer() {
        for (String h : new String[]{"192.168.178.2", "10.0.0.1", "172.16.0.1", "172.31.255.1", "127.0.0.1",
                "169.254.1.1", "hydra", "hydra.fritz.box", "nas.local", "x.home.arpa", "fd00::2", "::1", "fe80::1"}) {
            assertTrue(h, Logic.isLocal(h));
        }
        for (String h : new String[]{"172.32.0.1", "8.8.8.8", "hydra.example.org", "2001:db8::1", "", "192.168.1"}) {
            assertFalse(h, Logic.isLocal(h));
        }
    }

    @Test public void codeWirdGesaeubert() {
        assertEquals("K7QM2XPAB3CD", Logic.cleanCode(" k7qm-2xpa-b3cd "));
        assertNull(Logic.cleanCode("K7QM-2XPA-B3C"));
        assertNull(Logic.cleanCode("K7QM-2XPA-B3C0"));          // 0 gibt es im Alphabet nicht
        assertNull(Logic.cleanCode("K7QM-2XPA-B3CI"));          // I ebenso
        assertNull(Logic.cleanCode(null));
    }

    @Test public void fingerabdruckKurzUndWieDerServer() {
        String hex = Logic.spkiHex("abc".getBytes(StandardCharsets.US_ASCII));
        assertEquals("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", hex);
        assertEquals("BA78 16BF 8F01", Logic.shortPin(hex));
        assertEquals("", Logic.shortPin("zu-kurz"));
        assertEquals("", Logic.shortPin(null));
    }
}
