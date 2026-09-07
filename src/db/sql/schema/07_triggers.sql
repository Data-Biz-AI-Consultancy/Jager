-- Triggers: cascade-delete embeddings when staging content changes

CREATE OR REPLACE FUNCTION m_staging.delete_old_notion_embeddings()
RETURNS TRIGGER AS $$
BEGIN
	DELETE FROM m_embeddings.notion_pages WHERE source_id = OLD.id;
	RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_delete_old_notion_embeddings ON m_staging.notion_pages;
CREATE TRIGGER trg_delete_old_notion_embeddings
BEFORE UPDATE ON m_staging.notion_pages
FOR EACH ROW
WHEN (OLD.cleaned_content IS DISTINCT FROM NEW.cleaned_content)
EXECUTE FUNCTION m_staging.delete_old_notion_embeddings();


CREATE OR REPLACE FUNCTION m_staging.delete_old_substack_embeddings()
RETURNS TRIGGER AS $$
BEGIN
	DELETE FROM m_embeddings.substack_posts WHERE source_id = OLD.id;
	RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_delete_old_substack_embeddings ON m_staging.substack_posts;
CREATE TRIGGER trg_delete_old_substack_embeddings
BEFORE UPDATE ON m_staging.substack_posts
FOR EACH ROW
WHEN (OLD.cleaned_content IS DISTINCT FROM NEW.cleaned_content)
EXECUTE FUNCTION m_staging.delete_old_substack_embeddings();


CREATE OR REPLACE FUNCTION m_staging.delete_old_linkedin_embeddings()
RETURNS TRIGGER AS $$
BEGIN
	DELETE FROM m_embeddings.linkedin_posts WHERE source_id = OLD.id;
	RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_delete_old_linkedin_embeddings ON m_staging.linkedin_posts;
CREATE TRIGGER trg_delete_old_linkedin_embeddings
BEFORE UPDATE ON m_staging.linkedin_posts
FOR EACH ROW
WHEN (OLD.cleaned_content IS DISTINCT FROM NEW.cleaned_content)
EXECUTE FUNCTION m_staging.delete_old_linkedin_embeddings();
