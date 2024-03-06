{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    black
    python311Packages.pylint
    python311Packages.botocore
    python311Packages.boto3
  ];
}
