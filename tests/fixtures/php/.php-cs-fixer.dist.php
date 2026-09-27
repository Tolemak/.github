<?php

declare(strict_types=1);

$finder = (new PhpCsFixer\Finder())
    ->in([__DIR__.'/src', __DIR__.'/tests']);

return (new PhpCsFixer\Config())
    ->setRules([
        '@Symfony' => true,
        'declare_strict_types' => true,
    ])
    ->setRiskyAllowed(true)
    ->setCacheFile(__DIR__.'/var/.php-cs-fixer.cache')
    ->setFinder($finder);
