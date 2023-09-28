from monstr.client.client import Client
from monstr.client.event_handlers import EventAccepter
from monstr.event.event import Event
"""
    Probably this utility acceptors would make sense to move to monstr
    doc what each does properly though
    these are used where we want to filter events beyond what is possible from the basic filters we can pass to the
    relays 
"""

class PostsOnlyAcceptor(EventAccepter):

    def accept_event(self,
                     the_client: Client,
                     sub_id: str,
                     evt: Event) -> bool:
        ret = True
        e_tags = evt.get_tags('e')
        if e_tags:
            for c_tag in e_tags:
                # old style?
                if len(c_tag) == 1:
                    ret = False
                    break
                elif len(c_tag) >= 3:
                    t_val = str(c_tag[2]).lower()
                    if t_val == 'reply':
                        ret = False
                        break

        return ret


class RepliesOnlyAcceptor(PostsOnlyAcceptor):
    def accept_event(self,
                     the_client: Client,
                     sub_id: str,
                     evt: Event) -> bool:
        return not super().accept_event(the_client, sub_id, evt)