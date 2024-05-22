# probably we move these eventually into monstr


# class DynamicFilter(ABC):
#
#     @abstractmethod
#     async def ainit_filter(self):
#         pass


# class EventView:
#
#     def __init__(self,
#                  name: str,
#                  view_filter: [dict],
#                  path: str = None,
#                  view_acceptor: EventAccepter = None,
#                  filter_tracker: DynamicFilter = None):
#
#         self._name = name
#         self._path = path
#         self._full_name = name
#         if path:
#             self._full_name = f'{name}{path}'
#         else:
#             self._path = ''
#
#         self._view_filter = view_filter
#         self._view_acceptor = view_acceptor
#         self._filter_tracker = filter_tracker
#
#     @property
#     def name(self):
#         return self._name
#
#     @property
#     def full_name(self):
#         return self._full_name
#
#     @property
#     def path(self):
#         return self._path
#
#     @property
#     def view_filter(self):
#         return self._view_filter
#
#     @view_filter.setter
#     def view_filter(self, view_filter):
#         self._view_filter = view_filter
#
#     @property
#     def filter_tracker(self):
#         return self._filter_tracker
#
#     @property
#     def view_acceptor(self):
#         return self._view_acceptor
#
#     def __str__(self):
#         return self.full_name
#
#
# class UserContactsFilter(DynamicFilter):
#
#     def __init__(self,
#                  base_filter: dict,
#                  for_view: EventView,
#                  for_user: Keys,
#                  profile_handler: NetworkedProfileEventHandler):
#
#         self._base_filter = base_filter
#         self._for_view = for_view
#         self._for_user = for_user
#         self._profile_handler = profile_handler
#
#     async def ainit_filter(self):
#         contacts = await self._profile_handler.aload_contacts(self._for_user.public_key_hex())
#         self._bas
#
#         self._for_view.view_filter = {
#             'kinds': [1],
#             'authors': contacts.follow_keys(),
#             'limit': 40
#         }
#
#
# class CurrentUserFollowsPostsFilter(EventView):
#
#     def __init__(self,
#                  current_user: Keys,
#                  profile_handler: NetworkedProfileEventHandler):
#         self._current_user = current_user
#         self._profile_handler = profile_handler
#         self._filter_tracker = UserContactsFilter(for_view=self,
#                                                   for_user=current_user,
#                                                   profile_handler=profile_handler)
#
#         super().__init__(name='local',
#                          path='/user/follows/posts',
#                          view_filter=None,
#                          view_acceptor=PostsOnlyAcceptor(),
#                          filter_tracker=self._filter_tracker)
#
#
# class CurrentUserFollowsThreadsFilter(EventView):
#
#     def __init__(self,
#                  current_user: Keys,
#                  profile_handler: NetworkedProfileEventHandler):
#         self._current_user = current_user
#         self._profile_handler = profile_handler
#         self._filter_tracker = UserContactsFilter(for_view=self,
#                                                   for_user=current_user,
#                                                   profile_handler=profile_handler)
#
#         super().__init__(name='local',
#                          path='/user/follows/threads',
#                          view_filter=None,
#                          view_acceptor=RepliesOnlyAcceptor(),
#                          filter_tracker=self._filter_tracker)