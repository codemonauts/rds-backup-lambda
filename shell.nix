{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    black
    terraform
    python313Packages.pip
    python313Packages.pylint
    python313Packages.botocore
    python313Packages.boto3
    python313Packages.environs
    zip
  ];
}
