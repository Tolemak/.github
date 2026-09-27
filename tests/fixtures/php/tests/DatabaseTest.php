<?php

declare(strict_types=1);

namespace Fixture\Tests;

use PHPUnit\Framework\TestCase;

/**
 * Proves the optional PostgreSQL service of php-ci is reachable via DATABASE_URL.
 */
final class DatabaseTest extends TestCase
{
    public function testPostgresIsReachable(): void
    {
        $url = getenv('DATABASE_URL');
        if (false === $url || '' === $url) {
            self::markTestSkipped('DATABASE_URL is not set.');
        }

        $parts = parse_url($url);
        self::assertIsArray($parts);
        $dsn = sprintf(
            'pgsql:host=%s;port=%d;dbname=%s',
            $parts['host'] ?? '127.0.0.1',
            $parts['port'] ?? 5432,
            ltrim($parts['path'] ?? '', '/'),
        );
        $pdo = new \PDO($dsn, $parts['user'] ?? null, $parts['pass'] ?? null);

        $statement = $pdo->query('SELECT 1');

        self::assertNotFalse($statement);
        self::assertEquals(1, $statement->fetchColumn());
    }
}
