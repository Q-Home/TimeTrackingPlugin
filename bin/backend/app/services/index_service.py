class IndexService:
    def __init__(self, user_repository, badge_repository, log_repository):
        self.user_repository = user_repository
        self.badge_repository = badge_repository
        self.log_repository = log_repository

    def create_indexes(self):
        self.user_repository.create_indexes()
        self.badge_repository.create_indexes()
        self.log_repository.info("MongoDB indexes created")