package com.pulse.services;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/** Tests for {@link DiscordAlertService}. */
public class DiscordAlertServiceTest {
    private MockWebServer server;
    private DiscordAlertService service;

    @BeforeEach
    void setUp() throws Exception {
        server = new MockWebServer();
        server.start();
        service = new DiscordAlertService(server.url("/webhook").toString());
    }

    @AfterEach
    void tearDown() throws Exception {
        server.shutdown();
    }

    @Test
    void testSendAlertSuccess() throws Exception {
        server.enqueue(new MockResponse().setResponseCode(204));
        CompletableFuture<Boolean> future = service.sendAlert("hello");
        assertTrue(future.get(5, TimeUnit.SECONDS));
    }

    @Test
    void testSendAlertFailure() throws Exception {
        server.enqueue(new MockResponse().setResponseCode(500));
        CompletableFuture<Boolean> future = service.sendAlert("hello");
        assertFalse(future.get(5, TimeUnit.SECONDS));
    }
}
