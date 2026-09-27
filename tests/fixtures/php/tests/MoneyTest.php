<?php

declare(strict_types=1);

namespace Fixture\Tests;

use Fixture\Money;
use PHPUnit\Framework\TestCase;

final class MoneyTest extends TestCase
{
    public function testAdd(): void
    {
        $sum = (new Money(150, 'PLN'))->add(new Money(250, 'PLN'));

        self::assertSame(400, $sum->amount);
        self::assertSame('4.00 PLN', $sum->format());
    }

    public function testRejectsInvalidCurrency(): void
    {
        $this->expectException(\InvalidArgumentException::class);

        new Money(1, 'zł');
    }

    public function testRejectsMixedCurrencies(): void
    {
        $this->expectException(\LogicException::class);

        (new Money(1, 'PLN'))->add(new Money(1, 'EUR'));
    }

    public function testAllocateSpreadsRemainder(): void
    {
        $amounts = array_map(
            static fn (Money $m): int => $m->amount,
            (new Money(100, 'PLN'))->allocate(3),
        );

        self::assertSame([34, 33, 33], $amounts);
    }

    public function testAllocateRejectsZeroParts(): void
    {
        $this->expectException(\InvalidArgumentException::class);

        (new Money(100, 'PLN'))->allocate(0);
    }
}
