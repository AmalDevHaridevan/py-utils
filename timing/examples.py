from  method_timer import MethodTimer
import timeit
try:
   import torch
   TORCH_FOUND=True
except ModuleNotFoundError:
   TORCH_FOUND=False
# a simple wrapper, since list class def is immutable
class MyList(list):
    ...

if TORCH_FOUND:
    class MyNN(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.layer = torch.nn.Sequential(torch.nn.Linear(3,4),
                                            torch.nn.Tanh(),
                                            torch.nn.Linear(4,400),
                                            torch.nn.LeakyReLU(),
                                            torch.nn.Linear(400,1))

        def forward(self, x):
            return self.layer(x)

if __name__ == "__main__":
    # Lets time the list.append method of builtins list
    raw_list = MyList()
    wrapped_list = MethodTimer(raw_list)
    for i in range(1000):
        wrapped_list.append(i)
    # lets check the list.extend method
    for i in range(1000):
        wrapped_list.extend([i])
    # plot times
    wrapped_list.plot(('append', 'extend'))
    wrapped_list.plot_histograms(('append','extend'))
    method_times = wrapped_list.data_
    avg_append_time = method_times['append'].mean()
    avg_extend_time = method_times['extend'].mean()
    # compare with timeit
    avg_append_time_timeit = timeit.timeit("raw_list.append(1)", globals=dict(raw_list=raw_list), number=1000)/1000
    avg_extend_time_timeit = timeit.timeit("raw_list.extend([1])", globals=dict(raw_list=raw_list), number=1000)/1000
    print("Avg time measured for append using method timer: ", avg_append_time)
    print("Avg time measured for append using timeit timer: ", avg_append_time_timeit)
    print("Avg time measured for extend using method timer: ", avg_extend_time)
    print("Avg time measured for extend using timeit timer: ", avg_extend_time_timeit)
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # torch example
    if TORCH_FOUND:
        mod = MyNN()
        wrapped_mod = MethodTimer(mod)
        # first run to cache stuff
        mod(torch.rand(1,3))
        for i in range(100):
            wrapped_mod(torch.rand(1,3))
        timeit_avg = timeit.timeit("mod(torch.rand(1,3))", globals=dict(mod=mod, torch=torch), number=100)/100
        mod_avg = wrapped_mod.data_["forward"].mean()
        print("Avg time measured for forward pass using MethodTimer: ", mod_avg)
        print("Avg time measured for forward pass using timeit: ", timeit_avg)