INSERT INTO s_reddit.subreddits_monitored (name, active) VALUES 
('smallbusiness', TRUE),
('saas', TRUE),
('solopreneur', TRUE),
('indiebiz', TRUE),
('entrepreneurship', TRUE),
('advancedentrepreneur', TRUE),
('entrepreneurridealong', TRUE),
('growmybusiness', TRUE)
ON CONFLICT (name) DO NOTHING;

INSERT INTO s_substack.feeds_monitored (name, feed_url, active) 
VALUES 
('SeattleDataGuy', 'https://seattledataguy.substack.com/feed', TRUE),
('Decision', 'https://decision.substack.com/feed', TRUE),
('EngLeadership', 'https://newsletter.eng-leadership.com/feed', TRUE),
('ThrivingInEngineering', 'https://thrivinginengineering.substack.com/feed', TRUE),
('CodeLikeAGirl', 'https://codelikeagirl.substack.com/feed', TRUE),
('Data Biz', 'https://jimmypang.substack.com/feed', TRUE),
('Benn', 'https://benn.substack.com/feed', TRUE),
('nilukakavanagh', 'https://nilukakavanagh.substack.com/feed', TRUE),
('Datapreneur', 'https://nickvaliotti.substack.com/feed', TRUE)
ON CONFLICT (name) DO NOTHING;

INSERT INTO s_wordpress.feeds_monitored (name, feed_url, active) 
VALUES 
('Towards Data Science', 'https://towardsdatascience.com/feed', TRUE)
ON CONFLICT (name) DO NOTHING;

INSERT INTO s_notion.databases_monitored (database_id, name, type, active) VALUES 
('b5ad53f72b0e45e3b481e25da2703fd8', 'Leadership & Management', 'database', TRUE),
('1686e98d4ef8806da4e1c28268b7365e', 'Data Science - AIs', 'database', TRUE),
('4cd9498f5b5c48c6864d57bd36f7f82d', 'Data Science', 'database', TRUE),
('32fcdb5f301b4a9c94329dcadeffca15', 'data engineering', 'database', TRUE),
('f0501c9ac3bf4f0ea8d06b7ed6e40a31', 'Data Governance', 'database', TRUE),
('8fc4f5d17d6644eaa6b199f11cb3bf2b', 'Data Visualization & Reporting', 'database', TRUE),
('40906fc76abd4951bd4b283c9717d320', 'Product Management', 'database', TRUE),
('2bdfbb81d5c043d0a5fdd3028ad2504f', 'Product Analytics', 'database', TRUE),
('1d362ecd225241c0ab3c0fe4d0ed3cda', 'Software Engineering', 'database', TRUE),
('2d56e98d4ef8806ba96cca38539b67e1', 'Business', 'database', TRUE),
('f34619396f3c4be8b96fa64211eb18d7', 'Career', 'database', TRUE),
('3876e98d4ef8807eab9be1b0b029246c', 'Interview Meeting notes', 'meeting_notes', TRUE),
('3876e98d4ef880a6a61ae99d8912694f', 'Meetups & Seminars', 'meeting_notes', TRUE),
('3a36e98d4ef88084a1aec60052a3cb80', 'FaDi meeting notes', 'meeting_notes', TRUE)
ON CONFLICT (database_id) DO UPDATE SET name = EXCLUDED.name, type = EXCLUDED.type, active = TRUE;

INSERT INTO s_analytics.directives (directive) VALUES
('Find opportunities for Leads Generations for Data Biz'),
('Suggest new directives based on the existing available data'),
('Find gaps of the existing data availability and the directives')
ON CONFLICT (directive) DO NOTHING;
