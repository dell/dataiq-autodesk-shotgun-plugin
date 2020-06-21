# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
class PluginData:
    """Used in the PUT /plugins/<plugin> call to fill in the requisite data for the
    plugin.
    """

    def __init__(self, url: str, short_name: str, long_name: str, image: str):
        self.url = url
        self.short_name = short_name
        self.long_name = long_name
        self.image = image

    def __repr__(self):
        return f'{self.__class__.__name__}({self.url}, {self.short_name}, ' \
               f'{self.long_name}, {self.image})'
