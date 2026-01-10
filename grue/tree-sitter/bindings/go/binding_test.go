package tree_sitter_grue_test

import (
	"testing"

	tree_sitter "github.com/smacker/go-tree-sitter"
	"github.com/tree-sitter/tree-sitter-grue"
)

func TestCanLoadGrammar(t *testing.T) {
	language := tree_sitter.NewLanguage(tree_sitter_grue.Language())
	if language == nil {
		t.Errorf("Error loading Grue grammar")
	}
}
