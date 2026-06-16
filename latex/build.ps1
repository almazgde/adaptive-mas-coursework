$ErrorActionPreference = "Stop"

Push-Location $PSScriptRoot
try {
    xelatex -interaction=nonstopmode -halt-on-error coursework.tex
    if ($LASTEXITCODE -ne 0) { throw "xelatex failed with exit code $LASTEXITCODE" }

    if (Test-Path coursework.aux) {
        bibtex coursework
        if ($LASTEXITCODE -ne 0) { throw "bibtex failed with exit code $LASTEXITCODE" }
    }

    xelatex -interaction=nonstopmode -halt-on-error coursework.tex
    if ($LASTEXITCODE -ne 0) { throw "xelatex failed with exit code $LASTEXITCODE" }

    xelatex -interaction=nonstopmode -halt-on-error coursework.tex
    if ($LASTEXITCODE -ne 0) { throw "xelatex failed with exit code $LASTEXITCODE" }

    Write-Host "Built PDF: $PSScriptRoot\coursework.pdf"
}
finally {
    Pop-Location
}
