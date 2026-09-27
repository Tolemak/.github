<?php

declare(strict_types=1);

namespace Fixture;

final readonly class Money
{
    public function __construct(
        public int $amount,
        public string $currency,
    ) {
        if (1 !== preg_match('/^[A-Z]{3}$/', $currency)) {
            throw new \InvalidArgumentException(sprintf('Invalid currency "%s".', $currency));
        }
    }

    public function add(self $other): self
    {
        if ($other->currency !== $this->currency) {
            throw new \LogicException('Cannot add amounts in different currencies.');
        }

        return new self($this->amount + $other->amount, $this->currency);
    }

    /**
     * @return list<self>
     */
    public function allocate(int $parts): array
    {
        if ($parts < 1) {
            throw new \InvalidArgumentException('Parts must be positive.');
        }

        $base = intdiv($this->amount, $parts);
        $remainder = $this->amount % $parts;
        $result = [];
        for ($i = 0; $i < $parts; ++$i) {
            $result[] = new self($base + ($i < $remainder ? 1 : 0), $this->currency);
        }

        return $result;
    }

    public function format(): string
    {
        return sprintf('%s %s', number_format($this->amount / 100, 2, '.', ''), $this->currency);
    }
}
