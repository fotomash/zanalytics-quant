package com.pulse.services;

import java.io.IOException;
import java.util.concurrent.CompletableFuture;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

/**
 * Service for sending alerts to a Discord webhook asynchronously using OkHttp.
 */
public class DiscordAlertService {
    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");

    private final OkHttpClient client;
    private final String webhookUrl;

    public DiscordAlertService(String webhookUrl) {
        this(new OkHttpClient(), webhookUrl);
    }

    public DiscordAlertService(OkHttpClient client, String webhookUrl) {
        this.client = client;
        this.webhookUrl = webhookUrl;
    }

    /**
     * Send an alert message and complete the returned future with the result.
     *
     * @param message content to send to the webhook
     * @return future completed with {@code true} on success, {@code false} otherwise
     */
    public CompletableFuture<Boolean> sendAlert(String message) {
        CompletableFuture<Boolean> future = new CompletableFuture<>();
        RequestBody body = RequestBody.create("{\"content\":\"" + message + "\"}", JSON);
        Request request = new Request.Builder()
                .url(webhookUrl)
                .post(body)
                .build();

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                future.complete(false);
            }

            @Override
            public void onResponse(Call call, Response response) {
                try {
                    future.complete(response.isSuccessful());
                } finally {
                    response.close();
                }
            }
        });

        return future;
    }
}
