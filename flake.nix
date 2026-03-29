{
  description = "cryowire - dilution refrigerator wiring configuration management";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      nixpkgs,
      flake-utils,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python313;
        pythonPkgs = python.pkgs;

        cryowire = pythonPkgs.buildPythonPackage {
          pname = "cryowire";
          version = "0.0.0-dev";
          pyproject = true;

          src = ./.;

          env.SETUPTOOLS_SCM_PRETEND_VERSION = "0.0.0-dev";

          build-system = [
            pythonPkgs.hatchling
            pythonPkgs.hatch-vcs
          ];

          dependencies = [
            pythonPkgs.jsonschema
            pythonPkgs.matplotlib
            pythonPkgs.pydantic
            pythonPkgs.pyyaml
            pythonPkgs.rich
            pythonPkgs.typer
          ];

          nativeCheckInputs = [
            pythonPkgs.pytest
          ];

          checkPhase = ''
            runHook preCheck
            pytest tests/ -v
            runHook postCheck
          '';

          meta = {
            description = "JSON Schema validation for cryowire configuration files";
            homepage = "https://github.com/cryowire/cryowire";
            license = pkgs.lib.licenses.asl20;
          };
        };
      in
      {
        packages = {
          default = cryowire;
          inherit cryowire;
        };

        devShells.default = pkgs.mkShell {
          packages = [
            python
            pkgs.uv
          ];

          shellHook = ''
            echo "cryowire dev shell — Python $(python3 --version | cut -d' ' -f2), uv $(uv --version | cut -d' ' -f2)"
          '';
        };
      }
    );
}
