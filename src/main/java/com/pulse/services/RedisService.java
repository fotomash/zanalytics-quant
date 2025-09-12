package com.pulse.services;

import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;

/**
 * Simple wrapper around {@link JedisPool} providing basic Redis operations.
 */
public class RedisService {
    private final JedisPool jedisPool;

    /**
     * Create a service with a new {@link JedisPool} configured for the given host and port.
     */
    public RedisService(String host, int port) {
        this(new JedisPool(new JedisPoolConfig(), host, port));
    }

    /**
     * Create a service using the supplied {@link JedisPool} instance.
     */
    public RedisService(JedisPool jedisPool) {
        this.jedisPool = jedisPool;
    }

    /**
     * Set a string value for the provided key.
     */
    public void setKey(String key, String value) {
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.set(key, value);
        }
    }

    /**
     * Retrieve the value for the provided key.
     */
    public String getKey(String key) {
        try (Jedis jedis = jedisPool.getResource()) {
            return jedis.get(key);
        }
    }

    /**
     * Close the underlying {@link JedisPool}.
     */
    public void close() {
        jedisPool.close();
    }
}
