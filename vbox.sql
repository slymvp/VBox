--SELECT name FROM sqlite_master WHERE type='table';
delete from video_tv;
delete from video_movie;
delete from video_variety;
delete from video_cartoon;
delete from video_child;
delete from video_tv_ep;
delete from video_movie_ep;
delete from video_variety_ep;
delete from video_cartoon_ep;
delete from video_child_ep;
delete from user_watch_history;
delete from user_follow;
delete from user_bookmark;delete from sqlite_sequence;
delete from task_crawl;
delete from task_schedule;
delete from task_crawl_log;



drop table episodes;
commit;


CREATE TABLE episodes (
	id INTEGER NOT NULL, 
	series_id INTEGER NOT NULL, 
	episode_num VARCHAR(50) NOT NULL, 
	vid VARCHAR(100), 
	play_title VARCHAR(500), 
	union_title VARCHAR(500), 
	is_trailer BOOLEAN, 
	duration VARCHAR(50), 
	publish_date VARCHAR(50), 
	play_url TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id)
)
