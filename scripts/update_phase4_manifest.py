"""Compatibility entry point for rebuilding all Phase 4 outputs and their manifest."""
if __package__:
    from .build_features import main
else:
    from build_features import main

if __name__ == "__main__":
    main()
