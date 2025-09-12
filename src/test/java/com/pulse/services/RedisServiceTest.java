package com.pulse.services;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.github.fppt.jedismock.RedisServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import redis.clients.jedis.JedisPool;

/** Tests for {@link RedisService}. */
public class RedisServiceTest {
    private RedisServer server;
    private RedisService service;

    @BeforeEach
    void setUp() {
        server = RedisServer.newRedisServer().start();
        JedisPool pool = new JedisPool(server.getHost(), server.getBindPort());
        service = new RedisService(pool);
    }

    @AfterEach
    void tearDown() {
        service.close();
        server.stop();
    }

    @Test
    void testSetAndGetKey() {
        service.setKey("foo", "bar");
        assertEquals("bar", service.getKey("foo"));
    }
}
